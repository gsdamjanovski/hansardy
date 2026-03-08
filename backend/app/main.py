"""Hansardy API — RAG backend for Australian Hansard search."""

import json
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .classifier import ClassifiedQuery, classify_query
from .config import settings
from .generation import generate, generate_stream
from .models import AskRequest, AskResponse, SearchRequest, SearchResponse, Source
from .retrieval import classified_search, search, search_and_rerank

logger = logging.getLogger(__name__)

app = FastAPI(title="Hansardy", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://hansardy.vercel.app",
        "https://hansardy-*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def api_search(req: SearchRequest):
    """Semantic search against Hansard. Returns ranked source chunks."""
    sources = search(
        query=req.query,
        top_k=req.top_k,
        chamber=req.chamber,
        date_from=req.date_from,
        date_to=req.date_to,
        speaker=req.speaker,
        parliament_no=req.parliament_no,
    )
    return SearchResponse(query=req.query, sources=sources)


@app.post("/api/ask", response_model=AskResponse)
async def api_ask(req: AskRequest):
    """RAG query: classify → retrieve → re-rank → generate."""
    # 1. Classify
    try:
        classified = await classify_query(req.query)
    except Exception:
        logger.exception("Classification failed, falling back to default retrieval")
        classified = None

    # 2. Retrieve
    if classified:
        sources = classified_search(classified)
    else:
        sources = search_and_rerank(
            query=req.query,
            top_k=settings.search_top_k,
            rerank_top_n=settings.rerank_top_n,
            chamber=req.chamber,
            date_from=req.date_from,
            date_to=req.date_to,
            speaker=req.speaker,
            parliament_no=req.parliament_no,
        )

    # 3. Generate
    context_budget = classified.retrieval.context_budget_tokens if classified else None
    answer = generate(req.query, sources, context_budget_tokens=context_budget)

    return AskResponse(query=req.query, answer=answer, sources=sources)


@app.post("/api/ask/stream")
async def api_ask_stream(req: AskRequest):
    """Streaming RAG query via Server-Sent Events with query classification."""
    # 1. Classify
    classified: ClassifiedQuery | None = None
    try:
        classified = await classify_query(req.query)
    except Exception:
        logger.exception("Classification failed, falling back to default retrieval")

    # 2. Retrieve
    if classified:
        sources = classified_search(classified)
    else:
        sources = search_and_rerank(
            query=req.query,
            top_k=settings.search_top_k,
            rerank_top_n=settings.rerank_top_n,
            chamber=req.chamber,
            date_from=req.date_from,
            date_to=req.date_to,
            speaker=req.speaker,
            parliament_no=req.parliament_no,
        )

    # 3. Stream response
    context_budget = classified.retrieval.context_budget_tokens if classified else None

    async def event_generator():
        # Emit classification metadata
        if classified:
            metadata = {
                "query_type": classified.query_type.value,
                "rewritten_query": classified.rewritten_query,
                "strategy": classified.retrieval.strategy.value,
            }
            yield {"event": "metadata", "data": json.dumps(metadata)}

        # Emit sources
        sources_data = [s.model_dump() for s in sources]
        yield {"event": "sources", "data": json.dumps(sources_data)}

        # Stream the answer token by token
        for token in generate_stream(req.query, sources, context_budget_tokens=context_budget):
            yield {"event": "token", "data": token}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
