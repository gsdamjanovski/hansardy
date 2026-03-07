"""Hansardy API — RAG backend for Australian Hansard search."""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .generation import generate, generate_stream
from .models import AskRequest, AskResponse, SearchRequest, SearchResponse, Source
from .retrieval import search, search_and_rerank

app = FastAPI(title="Hansardy", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
def api_ask(req: AskRequest):
    """RAG query: retrieve Hansard chunks, then generate an answer with Opus."""
    # Retrieve and re-rank
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

    # Generate answer
    answer = generate(req.query, sources)
    return AskResponse(query=req.query, answer=answer, sources=sources)


@app.post("/api/ask/stream")
async def api_ask_stream(req: AskRequest):
    """Streaming RAG query via Server-Sent Events."""
    # Retrieve and re-rank
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

    # Send sources first, then stream the answer
    async def event_generator():
        # Emit sources as a single event
        sources_data = [s.model_dump() for s in sources]
        yield {"event": "sources", "data": json.dumps(sources_data)}

        # Stream the answer token by token
        for token in generate_stream(req.query, sources):
            yield {"event": "token", "data": token}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
