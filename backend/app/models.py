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


class SpeakerProfile(BaseModel):
    id: str
    canonical_name: str
    display_name: str
    primary_party: str
    era: str
    appearances: int
    chambers: list[str] = []
    year_start: int | None = None
    year_end: int | None = None
    date_of_birth: str | None = None
    date_of_death: str | None = None
    gender: str | None = None
    notable: str | None = None
    electorates: list[str] = []
    photo_url: str | None = None
    aph_id: str | None = None


class SearchResponse(BaseModel):
    query: str
    sources: list[Source]


class SpeakerSearchResponse(BaseModel):
    query: str
    speakers: list[SpeakerProfile]


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[Source]
    speakers: dict[str, SpeakerProfile] = {}
