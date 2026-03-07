from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    chamber: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    speaker: str | None = None
    parliament_no: int | None = None
    top_k: int = 20


class AskRequest(BaseModel):
    query: str
    chamber: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    speaker: str | None = None
    parliament_no: int | None = None


class Source(BaseModel):
    id: str
    text: str
    chamber: str
    sitting_date: str
    speakers: str
    parliament_no: int
    source_file: str
    score: float


class SearchResponse(BaseModel):
    query: str
    sources: list[Source]


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[Source]
