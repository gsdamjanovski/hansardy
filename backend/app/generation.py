"""Generation module — sends retrieved Hansard context to Opus for answering."""

from __future__ import annotations

from collections.abc import Generator

import anthropic

from .config import settings
from .models import SpeakerProfile, Source

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are Hansardy, a research assistant for Australian federal parliament.

You answer questions EXCLUSIVELY by drawing on the Hansard transcripts and speaker profiles provided below. You must NEVER use your own training knowledge to answer factual questions about politicians, debates, or parliamentary events.

RULES:
1. Every factual claim must cite a specific source using [Source ID] notation (e.g. [1], [2]).
2. If the retrieved context doesn't contain enough information to answer, say so explicitly — e.g. "I couldn't find enough information about [topic] in the Hansard records provided." Do NOT fill gaps with your own knowledge.
3. Never fabricate quotes. If you paraphrase, say "paraphrasing" or use indirect speech.
4. Use Australian English spelling throughout.
5. When comparing positions, present each side fairly before offering analysis.
6. Include relevant dates and parliamentary context (chamber, speaker, debate topic).
7. If a question is ambiguous, ask for clarification rather than guessing.
8. You may use speaker profile data (provided in <speaker_profiles> tags) to give biographical context, but clearly distinguish this from what appears in the Hansard excerpts.

CONTEXT FORMAT:
You will receive Hansard passages in <context> tags. Each has a numeric ID and metadata.
You may also receive structured speaker profiles in <speaker_profiles> tags.
Reference Hansard sources as [1], [2], etc. in your response. At the end of your response, list the sources you cited with their sitting date, chamber, and speaker(s)."""

# Rough estimate: 1 token ≈ 4 characters for English text
CHARS_PER_TOKEN = 4


def _build_speaker_profiles_block(
    speaker_profiles: dict[str, SpeakerProfile],
) -> str:
    """Format resolved speaker profiles into a block for the generation prompt."""
    if not speaker_profiles:
        return ""

    parts = []
    for name, profile in speaker_profiles.items():
        lines = [f'<speaker name="{name}">']
        lines.append(f"  <canonical_name>{profile.canonical_name}</canonical_name>")
        lines.append(f"  <display_name>{profile.display_name}</display_name>")
        lines.append(f"  <party>{profile.primary_party}</party>")
        lines.append(f"  <era>{profile.era}</era>")
        lines.append(f"  <appearances>{profile.appearances}</appearances>")
        if profile.chambers:
            lines.append(f"  <chambers>{', '.join(profile.chambers)}</chambers>")
        if profile.year_start:
            lines.append(f"  <year_start>{profile.year_start}</year_start>")
        if profile.year_end:
            lines.append(f"  <year_end>{profile.year_end}</year_end>")
        if profile.electorates:
            lines.append(f"  <electorates>{', '.join(profile.electorates)}</electorates>")
        if profile.notable:
            lines.append(f"  <notable>{profile.notable}</notable>")
        if profile.date_of_birth:
            lines.append(f"  <date_of_birth>{profile.date_of_birth}</date_of_birth>")
        if profile.date_of_death:
            lines.append(f"  <date_of_death>{profile.date_of_death}</date_of_death>")
        if profile.gender:
            lines.append(f"  <gender>{profile.gender}</gender>")
        lines.append("</speaker>")
        parts.append("\n".join(lines))

    return "<speaker_profiles>\n" + "\n\n".join(parts) + "\n</speaker_profiles>"


def _build_context_block(
    sources: list[Source],
    context_budget_tokens: int | None = None,
) -> str:
    """Format retrieved sources into a context block for Opus.

    If context_budget_tokens is provided, include sources until the budget is
    approximately exhausted (measured by character count / CHARS_PER_TOKEN).
    """
    budget_chars = (context_budget_tokens * CHARS_PER_TOKEN) if context_budget_tokens else None
    parts = []
    running_chars = 0

    for i, source in enumerate(sources, 1):
        block = (
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

        if budget_chars is not None:
            block_chars = len(block)
            if running_chars + block_chars > budget_chars and parts:
                break  # Budget exhausted; keep at least one source
            running_chars += block_chars

        parts.append(block)

    return "<context>\n" + "\n\n".join(parts) + "\n</context>"


def _build_user_message(
    query: str,
    sources: list[Source],
    context_budget_tokens: int | None = None,
    speaker_profiles: dict[str, SpeakerProfile] | None = None,
) -> str:
    """Assemble the full user message with context, speaker profiles, and query."""
    parts = [_build_context_block(sources, context_budget_tokens)]

    profiles_block = _build_speaker_profiles_block(speaker_profiles or {})
    if profiles_block:
        parts.append(profiles_block)

    parts.append(f"Question: {query}")
    return "\n\n".join(parts)


def generate(
    query: str,
    sources: list[Source],
    context_budget_tokens: int | None = None,
    speaker_profiles: dict[str, SpeakerProfile] | None = None,
) -> str:
    """Generate a non-streaming answer from Opus given a query and retrieved sources."""
    user_message = _build_user_message(query, sources, context_budget_tokens, speaker_profiles)

    response = client.messages.create(
        model=settings.generation_model,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def generate_stream(
    query: str,
    sources: list[Source],
    context_budget_tokens: int | None = None,
    speaker_profiles: dict[str, SpeakerProfile] | None = None,
) -> Generator[str, None, None]:
    """Stream an answer from Opus token-by-token."""
    user_message = _build_user_message(query, sources, context_budget_tokens, speaker_profiles)

    with client.messages.stream(
        model=settings.generation_model,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text
