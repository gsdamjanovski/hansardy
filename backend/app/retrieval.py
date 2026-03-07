"""Retrieval module — searches the Laslow Pinecone index for Hansard chunks."""

from pinecone import Pinecone

from .config import settings
from .models import Source

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
