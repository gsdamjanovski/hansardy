"""Generation module — sends retrieved Hansard context to Opus for answering."""

from collections.abc import Generator

import anthropic

from .config import settings
from .models import Source

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are Hansardy, a research assistant for Australian federal parliament.

You answer questions by drawing on Hansard transcripts — the official record of debates in the House of Representatives and the Senate.

RULES:
1. Every factual claim must cite a specific source using [Source ID] notation (e.g. [1], [2]).
2. If the retrieved context doesn't contain enough information to answer, say so explicitly. Do not guess.
3. Never fabricate quotes. If you paraphrase, say "paraphrasing" or use indirect speech.
4. Use Australian English spelling throughout.
5. When comparing positions, present each side fairly before offering analysis.
6. Include relevant dates and parliamentary context (chamber, speaker, debate topic).
7. If a question is ambiguous, ask for clarification rather than guessing.

CONTEXT FORMAT:
You will receive Hansard passages in <context> tags. Each has a numeric ID and metadata.
Reference them as [1], [2], etc. in your response. At the end of your response, list the sources you cited with their sitting date, chamber, and speaker(s)."""


def _build_context_block(sources: list[Source]) -> str:
    """Format retrieved sources into a context block for Opus."""
    parts = []
    for i, source in enumerate(sources, 1):
        parts.append(
            f'<source id="{i}">\n'
            f"  <metadata>\n"
            f"    <sitting_date>{source.sitting_date}</sitting_date>\n"
            f"    <chamber>{source.chamber}</chamber>\n"
            f"    <speakers>{source.speakers}</speakers>\n"
            f"    <parliament_no>{source.parliament_no}</parliament_no>\n"
            f"    <source_file>{source.source_file}</source_file>\n"
            f"  </metadata>\n"
            f"  <text>\n{source.text}\n  </text>\n"
            f"</source>"
        )
    return "<context>\n" + "\n\n".join(parts) + "\n</context>"


def generate(query: str, sources: list[Source]) -> str:
    """Generate a non-streaming answer from Opus given a query and retrieved sources."""
    context = _build_context_block(sources)
    user_message = f"{context}\n\nQuestion: {query}"

    response = client.messages.create(
        model=settings.generation_model,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def generate_stream(query: str, sources: list[Source]) -> Generator[str, None, None]:
    """Stream an answer from Opus token-by-token."""
    context = _build_context_block(sources)
    user_message = f"{context}\n\nQuestion: {query}"

    with client.messages.stream(
        model=settings.generation_model,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text
