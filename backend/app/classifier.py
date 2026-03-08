"""Query classifier — Haiku-powered routing layer for intelligent retrieval."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

import anthropic
from pydantic import BaseModel, Field

from .config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


class QueryType(StrEnum):
    FACTUAL_LOOKUP = "FACTUAL_LOOKUP"
    TEMPORAL = "TEMPORAL"
    THEMATIC = "THEMATIC"
    COMPARISON = "COMPARISON"
    SPEAKER_PROFILE = "SPEAKER_PROFILE"
    EXPLORATORY = "EXPLORATORY"


class RetrievalStrategy(StrEnum):
    SINGLE = "single"
    MULTI = "multi"
    TEMPORAL = "temporal"


class Entities(BaseModel):
    speakers: list[str] = Field(default_factory=list)
    parties: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    chambers: list[str] = Field(default_factory=list)
    bills: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class RetrievalParams(BaseModel):
    top_k: int = 20
    strategy: RetrievalStrategy = RetrievalStrategy.SINGLE
    sub_queries: list[str] = Field(default_factory=list)
    context_budget_tokens: int = 5000


class ClassifiedQuery(BaseModel):
    query_type: QueryType
    entities: Entities
    pinecone_filters: dict = Field(default_factory=dict)
    retrieval: RetrievalParams
    rewritten_query: str


CLASSIFIER_PROMPT = f"""You are a query classifier for an Australian parliamentary Hansard search system.

Given a user query, output JSON with:

{{
  "query_type": "FACTUAL_LOOKUP|TEMPORAL|THEMATIC|COMPARISON|SPEAKER_PROFILE|EXPLORATORY",
  "entities": {{
    "speakers": [],
    "parties": [],
    "date_from": null,
    "date_to": null,
    "chambers": [],
    "bills": [],
    "topics": []
  }},
  "pinecone_filters": {{}},
  "retrieval": {{
    "top_k": 10,
    "strategy": "single|multi|temporal",
    "sub_queries": [],
    "context_budget_tokens": 5000
  }},
  "rewritten_query": ""
}}

QUERY TYPE GUIDELINES:
- FACTUAL_LOOKUP: Specific question about what someone said or a specific event. top_k=10, context_budget=5000.
- TEMPORAL: Time-bounded query ("last week", "this session", specific date range). top_k=15, context_budget=8000.
- THEMATIC: Broad policy/topic evolution over time. top_k=30-50, context_budget=15000.
- COMPARISON: Comparing positions of parties/speakers. strategy="multi", top_k=20-30, context_budget=20000.
- SPEAKER_PROFILE: Questions about a specific person's positions/record. top_k=20, context_budget=12000.
- EXPLORATORY: Open-ended or unclear queries. top_k=20, context_budget=12000.

RULES:
- "last week/month/year" → calculate date ranges from today ({date.today().isoformat()}).
- "recently" or "lately" → last 3 months.
- Speaker names → include full name in rewritten_query for semantic matching.
- For COMPARISON queries, generate sub_queries (one per entity being compared).
- For THEMATIC queries with broad time ranges, consider decomposing into time-windowed sub_queries.
- If the query mentions a specific bill, extract the bill name and include it in rewritten_query.
- Default to EXPLORATORY if uncertain.
- Australian political context: know the major parties (Labor, Liberal, Nationals, Greens), current PM (Albanese), key ministers.

PINECONE FILTER FORMAT:
- Chamber filter: {{"chamber": {{"$eq": "Senate"}}}} or {{"chamber": {{"$eq": "House of Representatives"}}}}
- Date range: {{"$and": [{{"sitting_date": {{"$gte": "2024-01-01"}}}}, {{"sitting_date": {{"$lte": "2024-12-31"}}}}]}}
- Combine with $and: {{"$and": [filter1, filter2, ...]}}
- Do NOT filter on speakers (use rewritten_query for semantic matching instead).
- Only include filters you are confident about. An empty {{}} is fine.

REWRITTEN QUERY:
- Strip filler words, focus on substance.
- Include speaker names, bill names, and key topic terms.
- Optimise for embedding-based semantic search.
- For COMPARISON, the rewritten_query should cover the overall topic (sub_queries handle each entity).

Respond with valid JSON only. No markdown, no explanation."""


async def classify_query(
    query: str,
    conversation_history: list[dict] | None = None,
) -> ClassifiedQuery:
    """Classify a user query and generate retrieval parameters.

    Args:
        query: The raw user query string.
        conversation_history: Optional prior messages for context-aware classification.

    Returns:
        ClassifiedQuery with type, entities, filters, retrieval params, and rewritten query.
    """
    messages = []

    # Include conversation history for context-aware classification
    if conversation_history:
        # Send a condensed version of prior exchanges
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in conversation_history[-4:]  # Last 2 exchanges
        )
        messages.append({
            "role": "user",
            "content": f"Conversation context:\n{history_text}\n\nClassify this new query: {query}",
        })
    else:
        messages.append({"role": "user", "content": query})

    response = client.messages.create(
        model=settings.classifier_model,
        max_tokens=500,
        system=CLASSIFIER_PROMPT,
        messages=messages,
    )

    raw = response.content[0].text.strip()

    # Handle potential markdown wrapping from the model
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return ClassifiedQuery.model_validate_json(raw)
