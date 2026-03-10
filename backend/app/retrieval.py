"""Retrieval module — searches the Laslow Pinecone index for Hansard chunks."""

from __future__ import annotations

import logging
import re

from pinecone import Pinecone

from .config import settings
from .models import Source, SpeakerProfile

logger = logging.getLogger(__name__)

# Avoid circular import — ClassifiedQuery is only used for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .classifier import ClassifiedQuery

pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)


def _build_filters(
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    speaker: str | None = None,
    parliament_no: int | None = None,
) -> dict | None:
    """Build a Pinecone metadata filter dict from optional parameters."""
    conditions = []

    if chamber:
        conditions.append({"chamber": {"$eq": chamber}})
    if speaker:
        # speakers field is comma-separated; $eq works for single-speaker chunks,
        # but for multi-speaker chunks we need a text match approach.
        # For MVP, use $eq which matches the full string value.
        # TODO: Switch to a more flexible matching strategy after enrichment.
        conditions.append({"speakers": {"$eq": speaker}})
    if parliament_no is not None:
        conditions.append({"parliament_no": {"$eq": parliament_no}})
    if date_from and date_to:
        conditions.append({"sitting_date": {"$gte": date_from}})
        conditions.append({"sitting_date": {"$lte": date_to}})
    elif date_from:
        conditions.append({"sitting_date": {"$gte": date_from}})
    elif date_to:
        conditions.append({"sitting_date": {"$lte": date_to}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _match_to_source(match, score: float | None = None) -> Source:
    """Convert a Pinecone match object to a Source model."""
    md = match.get("metadata", {}) if isinstance(match, dict) else match.metadata
    match_id = match.get("id", "") if isinstance(match, dict) else match.id
    match_score = score if score is not None else (
        match.get("score", 0.0) if isinstance(match, dict) else getattr(match, "score", 0.0)
    )
    return Source(
        id=match_id,
        text=md.get("text", ""),
        chamber=md.get("chamber", ""),
        sitting_date=md.get("sitting_date", ""),
        speakers=md.get("speakers", ""),
        parliament_no=md.get("parliament_no", 0),
        source_file=md.get("source_file", ""),
        score=match_score,
    )


def search(
    query: str,
    top_k: int = 20,
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    speaker: str | None = None,
    parliament_no: int | None = None,
) -> list[Source]:
    """Semantic search against the Laslow index using integrated inference."""
    filters = _build_filters(chamber, date_from, date_to, speaker, parliament_no)

    # Embed the query server-side via Pinecone integrated inference
    embedding = pc.inference.embed(
        model=settings.embedding_model,
        inputs=[query],
        parameters={"input_type": "query"},
    )

    query_kwargs = {
        "namespace": settings.pinecone_namespace,
        "vector": embedding.data[0].values,
        "top_k": top_k,
        "include_metadata": True,
    }
    if filters:
        query_kwargs["filter"] = filters

    results = index.query(**query_kwargs)
    return [_match_to_source(m) for m in results.matches]


def search_and_rerank(
    query: str,
    top_k: int = 20,
    rerank_top_n: int | None = None,
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    speaker: str | None = None,
    parliament_no: int | None = None,
) -> list[Source]:
    """Search then re-rank using cohere-rerank-3.5 via Pinecone."""
    top_n = rerank_top_n or settings.rerank_top_n

    # First: retrieve a broad set of candidates
    candidates = search(
        query=query,
        top_k=top_k,
        chamber=chamber,
        date_from=date_from,
        date_to=date_to,
        speaker=speaker,
        parliament_no=parliament_no,
    )

    if not candidates:
        return []

    # Re-rank the candidates
    documents = [{"id": s.id, "text": s.text} for s in candidates]
    reranked = pc.inference.rerank(
        model=settings.rerank_model,
        query=query,
        documents=documents,
        top_n=top_n,
        return_documents=True,
    )

    # Map reranked results back to Source objects
    candidate_map = {s.id: s for s in candidates}
    results = []
    for item in reranked.data:
        doc = item.document
        source_id = doc.get("id", "")
        if source_id in candidate_map:
            original = candidate_map[source_id]
            results.append(Source(
                id=original.id,
                text=original.text,
                chamber=original.chamber,
                sitting_date=original.sitting_date,
                speakers=original.speakers,
                parliament_no=original.parliament_no,
                source_file=original.source_file,
                score=item.score,
            ))
    return results


# ---------------------------------------------------------------------------
# Classified query retrieval — uses ClassifiedQuery to drive search strategy
# ---------------------------------------------------------------------------


def search_with_raw_filters(
    query: str,
    top_k: int = 20,
    raw_filters: dict | None = None,
) -> list[Source]:
    """Semantic search with a raw Pinecone filter dict (from the classifier)."""
    embedding = pc.inference.embed(
        model=settings.embedding_model,
        inputs=[query],
        parameters={"input_type": "query"},
    )

    query_kwargs = {
        "namespace": settings.pinecone_namespace,
        "vector": embedding.data[0].values,
        "top_k": top_k,
        "include_metadata": True,
    }
    if raw_filters:
        query_kwargs["filter"] = raw_filters

    results = index.query(**query_kwargs)
    return [_match_to_source(m) for m in results.matches]


def classified_search(classified: ClassifiedQuery) -> list[Source]:
    """Route retrieval based on classified query strategy."""
    strategy = classified.retrieval.strategy

    if strategy == "multi" and classified.retrieval.sub_queries:
        return _multi_search(classified)
    elif strategy == "temporal":
        return _temporal_search(classified)
    else:
        return _single_classified_search(classified)


def _single_classified_search(classified: ClassifiedQuery) -> list[Source]:
    """Single search with classifier-generated filters + rewritten query, then rerank."""
    filters = classified.pinecone_filters or None

    candidates = search_with_raw_filters(
        query=classified.rewritten_query,
        top_k=classified.retrieval.top_k,
        raw_filters=filters,
    )

    if not candidates:
        return []

    # Re-rank
    documents = [{"id": s.id, "text": s.text} for s in candidates]
    reranked = pc.inference.rerank(
        model=settings.rerank_model,
        query=classified.rewritten_query,
        documents=documents,
        top_n=settings.rerank_top_n,
        return_documents=True,
    )

    candidate_map = {s.id: s for s in candidates}
    results = []
    for item in reranked.data:
        doc = item.document
        source_id = doc.get("id", "")
        if source_id in candidate_map:
            original = candidate_map[source_id]
            results.append(Source(
                id=original.id,
                text=original.text,
                chamber=original.chamber,
                sitting_date=original.sitting_date,
                speakers=original.speakers,
                parliament_no=original.parliament_no,
                source_file=original.source_file,
                score=item.score,
            ))
    return results


def _multi_search(classified: ClassifiedQuery) -> list[Source]:
    """Run sub-queries in sequence, then merge and re-rank for balanced results.

    For COMPARISON queries, each sub_query targets one entity (e.g. one party/speaker).
    Results are interleaved to ensure balanced representation.
    """
    all_candidates: list[Source] = []
    seen_ids: set[str] = set()
    filters = classified.pinecone_filters or None

    # Per-sub-query top_k: split budget across sub-queries
    sub_top_k = max(10, classified.retrieval.top_k // len(classified.retrieval.sub_queries))

    for sub_query in classified.retrieval.sub_queries:
        candidates = search_with_raw_filters(
            query=sub_query,
            top_k=sub_top_k,
            raw_filters=filters,
        )
        # Deduplicate across sub-queries
        for c in candidates:
            if c.id not in seen_ids:
                seen_ids.add(c.id)
                all_candidates.append(c)

    if not all_candidates:
        return []

    # Re-rank all candidates against the original rewritten query
    documents = [{"id": s.id, "text": s.text} for s in all_candidates]
    reranked = pc.inference.rerank(
        model=settings.rerank_model,
        query=classified.rewritten_query,
        documents=documents,
        top_n=min(settings.rerank_top_n * 2, len(all_candidates)),  # Wider net for comparison
        return_documents=True,
    )

    candidate_map = {s.id: s for s in all_candidates}
    results = []
    for item in reranked.data:
        doc = item.document
        source_id = doc.get("id", "")
        if source_id in candidate_map:
            original = candidate_map[source_id]
            results.append(Source(
                id=original.id,
                text=original.text,
                chamber=original.chamber,
                sitting_date=original.sitting_date,
                speakers=original.speakers,
                parliament_no=original.parliament_no,
                source_file=original.source_file,
                score=item.score,
            ))
    return results


def _temporal_search(classified: ClassifiedQuery) -> list[Source]:
    """Temporal search — same as single but results sorted by date after re-ranking."""
    results = _single_classified_search(classified)
    # Sort by sitting_date descending (most recent first)
    results.sort(key=lambda s: s.sitting_date, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Speaker profile retrieval — queries the speakers namespace
# ---------------------------------------------------------------------------

_CITATION_RE = re.compile(r"\[\d+\]")


def clean_speaker_metadata(meta: dict, vector_id: str = "") -> SpeakerProfile:
    """Strip citation artifacts and build a SpeakerProfile from Pinecone metadata."""

    def _clean_str(val: str) -> str:
        return _CITATION_RE.sub("", val).strip()

    return SpeakerProfile(
        id=vector_id,
        canonical_name=_clean_str(meta.get("canonical_name", "")),
        display_name=_clean_str(meta.get("display_name", "")),
        primary_party=_clean_str(meta.get("primary_party", "")),
        era=meta.get("era", ""),
        appearances=meta.get("appearances", 0),
        chambers=meta.get("chambers", []),
        year_start=meta.get("year_start"),
        year_end=meta.get("year_end"),
        date_of_birth=_clean_str(meta.get("date_of_birth", "")) or None,
        date_of_death=_clean_str(meta.get("date_of_death", "")) or None,
        gender=meta.get("gender"),
        notable=_clean_str(meta.get("notable", "")) or None,
        electorates=meta.get("electorates", []),
        photo_url=meta.get("photo_url"),
        aph_id=meta.get("aph_id"),
    )


def search_speakers(query: str, limit: int = 5) -> list[SpeakerProfile]:
    """Semantic search for speaker profiles in the speakers namespace."""
    embedding = pc.inference.embed(
        model=settings.embedding_model,
        inputs=[query],
        parameters={"input_type": "query"},
    )

    results = index.query(
        vector=embedding.data[0].values,
        namespace=settings.speakers_namespace,
        top_k=limit,
        include_metadata=True,
        filter={"type": {"$eq": "speaker_bio"}},
    )

    return [clean_speaker_metadata(m.metadata, m.id) for m in results.matches]


def fetch_speaker(speaker_id: str) -> SpeakerProfile | None:
    """Fetch a single speaker profile by vector ID."""
    result = index.fetch(ids=[speaker_id], namespace=settings.speakers_namespace)
    if not result.vectors or speaker_id not in result.vectors:
        return None
    vec = result.vectors[speaker_id]
    return clean_speaker_metadata(vec.metadata, speaker_id)


def resolve_speaker_profiles(
    sources: list[Source],
    score_threshold: float = 0.7,
) -> dict[str, SpeakerProfile]:
    """Extract unique speaker names from sources and look up their profiles.

    Uses batch embedding for efficiency: embeds all speaker names in one call,
    then queries the speakers namespace for each.
    """
    # Collect unique speaker names from sources
    speaker_names: set[str] = set()
    for source in sources:
        if source.speakers:
            # speakers_list metadata may not be on Source model,
            # so split the comma-separated speakers field
            for name in source.speakers.split(","):
                name = name.strip()
                if name:
                    speaker_names.add(name)

    if not speaker_names:
        return {}

    names_list = list(speaker_names)

    # Batch-embed all speaker names in one call
    embeddings = pc.inference.embed(
        model=settings.embedding_model,
        inputs=names_list,
        parameters={"input_type": "query"},
    )

    profiles: dict[str, SpeakerProfile] = {}
    seen_ids: set[str] = set()

    for name, emb in zip(names_list, embeddings.data):
        try:
            results = index.query(
                vector=emb.values,
                namespace=settings.speakers_namespace,
                top_k=1,
                include_metadata=True,
                filter={"type": {"$eq": "speaker_bio"}},
            )
            if results.matches and results.matches[0].score > score_threshold:
                match = results.matches[0]
                # Deduplicate: keep the first match per vector ID (higher appearances wins)
                if match.id not in seen_ids:
                    seen_ids.add(match.id)
                    profiles[name] = clean_speaker_metadata(match.metadata, match.id)
        except Exception:
            logger.warning("Failed to resolve speaker profile for %s", name, exc_info=True)

    return profiles
