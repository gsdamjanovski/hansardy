"""Tests for speaker profiles integration.

Validates:
1. clean_speaker_metadata strips citation artifacts
2. SpeakerProfile model serialization
3. resolve_speaker_profiles extracts and resolves speakers from sources
4. API endpoints (/api/speakers/search, /api/speakers/{id})
5. /api/ask includes speaker profiles in response
6. Golden question set integrity
7. Eval runner loading and filtering
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SPEAKER_META = {
    "type": "speaker_bio",
    "canonical_name": "Whitlam, Edward Gough[1]",
    "display_name": "Edward Gough Whitlam[1]",
    "primary_party": "Labor",
    "era": "pre-2006",
    "appearances": 542,
    "chambers": ["House of Representatives"],
    "year_start": 1953,
    "year_end": 1978,
    "date_of_birth": "1916-07-11[1]",
    "date_of_death": "2014-10-21",
    "gender": "Male",
    "notable": "21st Prime Minister of Australia[2], dismissed by the Governor-General in 1975[3].",
    "electorates": ["Werriwa"],
    "photo_url": "https://example.com/whitlam.jpg",
    "aph_id": "EZ5",
    "all_names": ["Whitlam", "Mr Whitlam", "Mr £ G Whitlam"],
}

SAMPLE_SPEAKER_META_MINIMAL = {
    "type": "speaker_bio",
    "canonical_name": "Smith, John",
    "display_name": "John Smith",
    "primary_party": "Liberal",
    "era": "2006+",
    "appearances": 10,
}

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "..", "eval", "golden_questions.json")


def _make_source(speakers: str):
    from app.models import Source

    return Source(
        id="chunk1", text="text", chamber="House",
        sitting_date="2024-01-01", speakers=speakers,
        parliament_no=47, source_file="2024-01-01.xml", score=0.9,
    )


# ---------------------------------------------------------------------------
# 1. clean_speaker_metadata
# ---------------------------------------------------------------------------


class TestCleanSpeakerMetadata:
    def test_strips_citation_artifacts(self):
        from app.retrieval import clean_speaker_metadata

        profile = clean_speaker_metadata(SAMPLE_SPEAKER_META, "speaker:whitlam:labor")

        assert profile.id == "speaker:whitlam:labor"
        assert profile.canonical_name == "Whitlam, Edward Gough"
        assert profile.display_name == "Edward Gough Whitlam"
        assert profile.date_of_birth == "1916-07-11"
        assert "[" not in (profile.notable or "")
        assert "]" not in (profile.notable or "")

    def test_notable_cleaned(self):
        from app.retrieval import clean_speaker_metadata

        profile = clean_speaker_metadata(SAMPLE_SPEAKER_META, "test")
        assert profile.notable == "21st Prime Minister of Australia, dismissed by the Governor-General in 1975."

    def test_preserves_clean_fields(self):
        from app.retrieval import clean_speaker_metadata

        profile = clean_speaker_metadata(SAMPLE_SPEAKER_META, "speaker:whitlam:labor")

        assert profile.primary_party == "Labor"
        assert profile.era == "pre-2006"
        assert profile.appearances == 542
        assert profile.chambers == ["House of Representatives"]
        assert profile.year_start == 1953
        assert profile.year_end == 1978
        assert profile.electorates == ["Werriwa"]
        assert profile.photo_url == "https://example.com/whitlam.jpg"
        assert profile.aph_id == "EZ5"

    def test_all_names_not_in_output(self):
        from app.retrieval import clean_speaker_metadata

        profile = clean_speaker_metadata(SAMPLE_SPEAKER_META, "test")
        dumped = profile.model_dump()
        assert "all_names" not in dumped

    def test_handles_minimal_metadata(self):
        from app.retrieval import clean_speaker_metadata

        profile = clean_speaker_metadata(SAMPLE_SPEAKER_META_MINIMAL, "test:id")

        assert profile.display_name == "John Smith"
        assert profile.chambers == []
        assert profile.year_start is None
        assert profile.date_of_birth is None
        assert profile.photo_url is None

    def test_empty_strings_become_none(self):
        from app.retrieval import clean_speaker_metadata

        meta = {
            **SAMPLE_SPEAKER_META_MINIMAL,
            "date_of_birth": "",
            "notable": "[1][2]",
        }
        profile = clean_speaker_metadata(meta, "test")
        assert profile.date_of_birth is None
        assert profile.notable is None


# ---------------------------------------------------------------------------
# 1b. Speaker profiles block for generation
# ---------------------------------------------------------------------------


class TestBuildSpeakerProfilesBlock:
    def test_empty_profiles_returns_empty_string(self):
        from app.generation import _build_speaker_profiles_block

        assert _build_speaker_profiles_block({}) == ""

    def test_includes_profile_fields(self):
        from app.generation import _build_speaker_profiles_block
        from app.models import SpeakerProfile

        profile = SpeakerProfile(
            id="speaker:whitlam:labor",
            canonical_name="Whitlam, Edward Gough",
            display_name="Edward Gough Whitlam",
            primary_party="Labor",
            era="pre-2006",
            appearances=542,
            chambers=["House of Representatives"],
            year_start=1953,
            year_end=1978,
            electorates=["Werriwa"],
            notable="21st Prime Minister of Australia",
        )
        block = _build_speaker_profiles_block({"Whitlam": profile})

        assert "<speaker_profiles>" in block
        assert 'name="Whitlam"' in block
        assert "<party>Labor</party>" in block
        assert "<notable>21st Prime Minister of Australia</notable>" in block
        assert "<electorates>Werriwa</electorates>" in block

    def test_included_in_user_message(self):
        from app.generation import _build_user_message
        from app.models import SpeakerProfile, Source

        source = Source(
            id="chunk1", text="text", chamber="House",
            sitting_date="2024-01-01", speakers="Whitlam",
            parliament_no=47, source_file="2024-01-01.xml", score=0.9,
        )
        profile = SpeakerProfile(
            id="speaker:whitlam:labor",
            canonical_name="Whitlam, Edward Gough",
            display_name="Edward Gough Whitlam",
            primary_party="Labor", era="pre-2006", appearances=542,
        )
        msg = _build_user_message(
            "Tell me about Whitlam",
            [source],
            speaker_profiles={"Whitlam": profile},
        )
        assert "<speaker_profiles>" in msg
        assert "<context>" in msg
        assert "Question: Tell me about Whitlam" in msg


# ---------------------------------------------------------------------------
# 2. SpeakerProfile model
# ---------------------------------------------------------------------------


class TestSpeakerProfileModel:
    def test_serialization(self):
        from app.models import SpeakerProfile

        profile = SpeakerProfile(
            id="speaker:test:labor", canonical_name="Test, Person",
            display_name="Person Test", primary_party="Labor",
            era="2006+", appearances=100, chambers=["Senate"],
            year_start=2010, year_end=2020, notable="A test senator.",
        )
        data = profile.model_dump()
        assert data["id"] == "speaker:test:labor"
        assert data["chambers"] == ["Senate"]
        assert data["photo_url"] is None

    def test_ask_response_includes_speakers(self):
        from app.models import AskResponse, SpeakerProfile, Source

        source = Source(
            id="chunk1", text="Some text", chamber="Senate",
            sitting_date="2024-01-01", speakers="Person Test",
            parliament_no=47, source_file="2024-01-01.xml", score=0.95,
        )
        profile = SpeakerProfile(
            id="speaker:test:labor", canonical_name="Test, Person",
            display_name="Person Test", primary_party="Labor",
            era="2006+", appearances=100,
        )
        response = AskResponse(
            query="test", answer="test answer",
            sources=[source], speakers={"Person Test": profile},
        )
        data = response.model_dump()
        assert "speakers" in data
        assert "Person Test" in data["speakers"]
        assert data["speakers"]["Person Test"]["primary_party"] == "Labor"

    def test_ask_response_empty_speakers_default(self):
        from app.models import AskResponse

        response = AskResponse(query="test", answer="answer", sources=[])
        assert response.speakers == {}

    def test_speaker_search_response(self):
        from app.models import SpeakerProfile, SpeakerSearchResponse

        profile = SpeakerProfile(
            id="test", canonical_name="A", display_name="B",
            primary_party="C", era="D", appearances=1,
        )
        resp = SpeakerSearchResponse(query="test", speakers=[profile])
        assert len(resp.speakers) == 1


# ---------------------------------------------------------------------------
# 3. resolve_speaker_profiles
# ---------------------------------------------------------------------------


class TestResolveSpeakerProfiles:
    def test_resolves_speakers_from_sources(self):
        from app.retrieval import index, pc, resolve_speaker_profiles

        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(data=[mock_emb])

        mock_match = SimpleNamespace(
            id="speaker:whitlam:labor", score=0.95,
            metadata=SAMPLE_SPEAKER_META,
        )
        index.query.return_value = SimpleNamespace(matches=[mock_match])

        profiles = resolve_speaker_profiles([_make_source("Whitlam")])

        assert "Whitlam" in profiles
        assert profiles["Whitlam"].display_name == "Edward Gough Whitlam"

    def test_skips_low_score_matches(self):
        from app.retrieval import index, pc, resolve_speaker_profiles

        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(data=[mock_emb])

        mock_match = SimpleNamespace(
            id="speaker:unknown:labor", score=0.3,
            metadata=SAMPLE_SPEAKER_META_MINIMAL,
        )
        index.query.return_value = SimpleNamespace(matches=[mock_match])

        profiles = resolve_speaker_profiles([_make_source("Unknown Person")])
        assert len(profiles) == 0

    def test_handles_empty_speakers(self):
        from app.retrieval import resolve_speaker_profiles

        profiles = resolve_speaker_profiles([_make_source("")])
        assert profiles == {}

    def test_splits_comma_separated_speakers(self):
        from app.retrieval import index, pc, resolve_speaker_profiles

        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(
            data=[mock_emb, mock_emb]
        )

        mock_match = SimpleNamespace(
            id="speaker:a:labor", score=0.9,
            metadata={**SAMPLE_SPEAKER_META_MINIMAL, "display_name": "Speaker A"},
        )
        index.query.return_value = SimpleNamespace(matches=[mock_match])

        profiles = resolve_speaker_profiles([_make_source("Speaker A, Speaker B")])

        call_args = pc.inference.embed.call_args
        assert len(call_args.kwargs["inputs"]) == 2

    def test_deduplicates_by_vector_id(self):
        from app.retrieval import index, pc, resolve_speaker_profiles

        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(
            data=[mock_emb, mock_emb]
        )

        mock_match = SimpleNamespace(
            id="speaker:whitlam:labor", score=0.95,
            metadata=SAMPLE_SPEAKER_META,
        )
        index.query.return_value = SimpleNamespace(matches=[mock_match])

        sources = [_make_source("Whitlam"), _make_source("Mr Whitlam")]
        profiles = resolve_speaker_profiles(sources)

        vector_ids = {p.id for p in profiles.values()}
        assert len(vector_ids) == 1


# ---------------------------------------------------------------------------
# 4. API endpoints
# ---------------------------------------------------------------------------


class TestSpeakerEndpoints:
    def test_speakers_search_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app
        from app.retrieval import index, pc

        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(data=[mock_emb])

        mock_match = SimpleNamespace(
            id="speaker:whitlam:labor", score=0.95,
            metadata=SAMPLE_SPEAKER_META,
        )
        index.query.return_value = SimpleNamespace(matches=[mock_match])

        client = TestClient(app)
        resp = client.get("/api/speakers/search?q=Whitlam")

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "Whitlam"
        assert len(data["speakers"]) == 1
        assert data["speakers"][0]["display_name"] == "Edward Gough Whitlam"
        assert "[" not in data["speakers"][0]["display_name"]

    def test_speaker_fetch_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app
        from app.retrieval import index

        vec = SimpleNamespace(metadata=SAMPLE_SPEAKER_META)
        index.fetch.return_value = SimpleNamespace(
            vectors={"speaker:whitlam:labor": vec}
        )

        client = TestClient(app)
        resp = client.get("/api/speakers/speaker:whitlam:labor")

        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_name"] == "Whitlam, Edward Gough"

    def test_speaker_fetch_not_found(self):
        from fastapi.testclient import TestClient

        from app.main import app
        from app.retrieval import index

        index.fetch.return_value = SimpleNamespace(vectors={})

        client = TestClient(app)
        resp = client.get("/api/speakers/speaker:nonexistent:party")

        assert resp.status_code == 404

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 5. /api/ask includes speakers
# ---------------------------------------------------------------------------


class TestAskWithSpeakers:
    def test_ask_returns_speaker_profiles(self):
        from fastapi.testclient import TestClient

        from app.generation import client as gen_client
        from app.main import app
        from app.retrieval import index, pc

        # Mock embedding
        mock_emb = SimpleNamespace(values=[0.1] * 1024)
        pc.inference.embed.return_value = SimpleNamespace(data=[mock_emb])

        # Hansard + speaker matches by namespace
        hansard_match = SimpleNamespace(
            id="chunk1", score=0.9,
            metadata={
                "text": "Mr Whitlam spoke about...",
                "chamber": "House of Representatives",
                "sitting_date": "1975-11-11",
                "speakers": "Whitlam",
                "parliament_no": 29,
                "source_file": "1975-11-11.xml",
            },
        )
        speaker_match = SimpleNamespace(
            id="speaker:whitlam:labor", score=0.95,
            metadata=SAMPLE_SPEAKER_META,
        )

        def mock_query(**kwargs):
            if kwargs.get("namespace") == "speakers":
                return SimpleNamespace(matches=[speaker_match])
            return SimpleNamespace(matches=[hansard_match])

        index.query.side_effect = mock_query

        # Mock reranker
        pc.inference.rerank.return_value = SimpleNamespace(
            data=[SimpleNamespace(
                document={"id": "chunk1", "text": "Mr Whitlam spoke about..."},
                score=0.95,
            )]
        )

        # Mock generation
        gen_client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="Whitlam spoke about dismissal [1].")]
        )

        client = TestClient(app)
        resp = client.post("/api/ask", json={"query": "What did Whitlam say?"})

        assert resp.status_code == 200
        data = resp.json()
        assert "speakers" in data
        assert "Whitlam" in data["speakers"]
        assert data["speakers"]["Whitlam"]["primary_party"] == "Labor"
        assert "[" not in data["speakers"]["Whitlam"]["display_name"]

        # Clean up side_effect for other tests
        index.query.side_effect = None


# ---------------------------------------------------------------------------
# 6. Golden question set integrity
# ---------------------------------------------------------------------------


class TestGoldenQuestions:
    def test_loads_and_has_65_questions(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        assert data["total_questions"] == 65
        assert len(data["questions"]) == 65

    def test_all_questions_have_required_fields(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        required = {"id", "query_type", "difficulty", "query", "expected_answer", "key_sources", "verification"}
        for q in data["questions"]:
            missing = required - set(q.keys())
            assert not missing, f"{q['id']} missing fields: {missing}"

    def test_query_type_distribution(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        types = {}
        for q in data["questions"]:
            types[q["query_type"]] = types.get(q["query_type"], 0) + 1
        assert types["FACTUAL_LOOKUP"] == 15
        assert types["TEMPORAL"] == 10
        assert types["THEMATIC"] == 10
        assert types["COMPARISON"] == 10
        assert types["SPEAKER_PROFILE"] == 10
        assert types["EXPLORATORY"] == 10

    def test_ids_are_unique(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        ids = [q["id"] for q in data["questions"]]
        assert len(ids) == len(set(ids))

    def test_difficulty_distribution(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        diffs = {}
        for q in data["questions"]:
            diffs[q["difficulty"]] = diffs.get(q["difficulty"], 0) + 1
        assert diffs["easy"] == data["difficulty_distribution"]["easy"]
        assert diffs["medium"] == data["difficulty_distribution"]["medium"]
        assert diffs["hard"] == data["difficulty_distribution"]["hard"]

    def test_hallucination_traps_present(self):
        with open(GOLDEN_PATH) as f:
            data = json.load(f)
        trap_ids = {q["id"] for q in data["questions"] if q.get("traps")}
        assert "FL-09" in trap_ids
        assert "SP-03" in trap_ids
        assert "T-03" in trap_ids
        assert "T-10" in trap_ids


# ---------------------------------------------------------------------------
# 7. Eval runner loading
# ---------------------------------------------------------------------------


class TestEvalRunner:
    def test_load_questions_all(self):
        from eval.eval_runner import load_questions
        assert len(load_questions()) == 65

    def test_load_questions_filter_by_ids(self):
        from eval.eval_runner import load_questions
        questions = load_questions(ids=["FL-01", "FL-09", "T-10"])
        assert len(questions) == 3
        assert {q["id"] for q in questions} == {"FL-01", "FL-09", "T-10"}

    def test_load_questions_filter_by_type(self):
        from eval.eval_runner import load_questions
        questions = load_questions(query_type="COMPARISON")
        assert len(questions) == 10
        assert all(q["query_type"] == "COMPARISON" for q in questions)

    def test_load_questions_filter_by_difficulty(self):
        from eval.eval_runner import load_questions
        questions = load_questions(difficulty="hard")
        assert all(q["difficulty"] == "hard" for q in questions)
        assert len(questions) == 17
