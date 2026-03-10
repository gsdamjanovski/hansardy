"""Evaluation runner for the Hansardy golden question set.

Runs all 65 golden questions against the live API and collects results
for manual scoring. Outputs a JSON report with answers, sources, metadata,
and auto-scored classification accuracy.

Usage:
    python -m eval.eval_runner                           # all questions
    python -m eval.eval_runner --ids FL-01 FL-09 T-10    # specific questions
    python -m eval.eval_runner --type COMPARISON          # by query type
    python -m eval.eval_runner --difficulty hard          # by difficulty
    python -m eval.eval_runner --api-url http://...      # custom API base

Output is written to eval/results/eval_YYYYMMDD_HHMMSS.json
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).parent
QUESTIONS_PATH = EVAL_DIR / "golden_questions.json"
RESULTS_DIR = EVAL_DIR / "results"

DEFAULT_API_URL = "http://localhost:8000"


def load_questions(
    ids: list[str] | None = None,
    query_type: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    """Load and optionally filter the golden question set."""
    with open(QUESTIONS_PATH) as f:
        data = json.load(f)

    questions = data["questions"]

    if ids:
        id_set = set(ids)
        questions = [q for q in questions if q["id"] in id_set]
    if query_type:
        questions = [q for q in questions if q["query_type"] == query_type.upper()]
    if difficulty:
        questions = [q for q in questions if q["difficulty"] == difficulty.lower()]

    return questions


def run_question(
    question: dict,
    api_url: str,
    client: httpx.Client,
    timeout: float = 120.0,
) -> dict:
    """Run a single question against the /api/ask endpoint and return results."""
    q_id = question["id"]
    query = question["query"]

    logger.info("Running %s: %s", q_id, query[:60])
    start = time.monotonic()

    try:
        resp = client.post(
            f"{api_url}/api/ask",
            json={"query": query},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.monotonic() - start

        # Auto-score classification if metadata is available
        # The /api/ask endpoint doesn't return query_type directly,
        # but the streaming endpoint does. We'll note expected type for manual scoring.
        sources = data.get("sources", [])
        speakers = data.get("speakers", {})

        return {
            "id": q_id,
            "query": query,
            "expected_type": question["query_type"],
            "difficulty": question["difficulty"],
            "answer": data.get("answer", ""),
            "source_count": len(sources),
            "source_ids": [s["id"] for s in sources[:10]],
            "source_speakers": list({
                s["speakers"] for s in sources if s.get("speakers")
            }),
            "source_date_range": _source_date_range(sources),
            "speaker_profiles_returned": list(speakers.keys()),
            "elapsed_seconds": round(elapsed, 2),
            "error": None,
            # Placeholders for manual scoring
            "scores": {
                "classification": None,
                "retrieval_p5": None,
                "retrieval_p10": None,
                "answer_accuracy": None,
                "citation_quality": None,
                "hallucination": None,
                "completeness": None,
            },
            "expected_answer": question["expected_answer"],
            "verification": question["verification"],
            "traps": question.get("traps", []),
        }
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.error("Failed %s after %.1fs: %s", q_id, elapsed, exc)
        return {
            "id": q_id,
            "query": query,
            "expected_type": question["query_type"],
            "difficulty": question["difficulty"],
            "answer": "",
            "source_count": 0,
            "source_ids": [],
            "source_speakers": [],
            "source_date_range": None,
            "speaker_profiles_returned": [],
            "elapsed_seconds": round(elapsed, 2),
            "error": str(exc),
            "scores": {
                "classification": None,
                "retrieval_p5": None,
                "retrieval_p10": None,
                "answer_accuracy": None,
                "citation_quality": None,
                "hallucination": None,
                "completeness": None,
            },
            "expected_answer": question["expected_answer"],
            "verification": question["verification"],
            "traps": question.get("traps", []),
        }


def _source_date_range(sources: list[dict]) -> dict | None:
    """Extract the min/max sitting dates from sources."""
    dates = [
        s["sitting_date"]
        for s in sources
        if s.get("sitting_date")
    ]
    if not dates:
        return None
    return {"earliest": min(dates), "latest": max(dates)}


def run_classification_check(
    questions: list[dict],
    api_url: str,
    client: httpx.Client,
    timeout: float = 30.0,
) -> dict[str, dict]:
    """Run queries through /api/ask/stream to capture classification metadata.

    Returns a dict mapping question ID to classification info.
    """
    classifications: dict[str, dict] = {}

    for question in questions:
        q_id = question["id"]
        try:
            with client.stream(
                "POST",
                f"{api_url}/api/ask/stream",
                json={"query": question["query"]},
                timeout=timeout,
            ) as resp:
                for line in resp.iter_lines():
                    if line.startswith("event: metadata"):
                        continue
                    if line.startswith("data: ") and "query_type" in line:
                        try:
                            meta = json.loads(line[6:])
                            actual_type = meta.get("query_type", "")
                            expected_type = question["query_type"]
                            classifications[q_id] = {
                                "actual_type": actual_type,
                                "expected_type": expected_type,
                                "correct": actual_type == expected_type,
                                "strategy": meta.get("strategy", ""),
                            }
                        except json.JSONDecodeError:
                            pass
                        break
        except Exception as exc:
            logger.warning("Classification check failed for %s: %s", q_id, exc)
            classifications[q_id] = {
                "actual_type": "ERROR",
                "expected_type": question["query_type"],
                "correct": False,
                "strategy": "",
            }

    return classifications


def compute_summary(results: list[dict], classifications: dict[str, dict]) -> dict:
    """Compute aggregate stats from results."""
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    successful = total - errors

    # Classification accuracy
    classified = [c for c in classifications.values() if c["actual_type"] != "ERROR"]
    classification_accuracy = (
        sum(1 for c in classified if c["correct"]) / len(classified)
        if classified
        else None
    )

    # Timing stats
    times = [r["elapsed_seconds"] for r in results if not r["error"]]
    avg_time = sum(times) / len(times) if times else None

    # Breakdown by type and difficulty
    by_type: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    for r in results:
        by_type[r["expected_type"]] = by_type.get(r["expected_type"], 0) + 1
        by_difficulty[r["difficulty"]] = by_difficulty.get(r["difficulty"], 0) + 1

    return {
        "total_questions": total,
        "successful": successful,
        "errors": errors,
        "classification_accuracy": classification_accuracy,
        "avg_response_seconds": round(avg_time, 2) if avg_time else None,
        "by_type": by_type,
        "by_difficulty": by_difficulty,
        "note": "Manual scoring fields (scores.*) are null — fill in after review.",
    }


def main():
    parser = argparse.ArgumentParser(description="Run Hansardy golden question evaluation")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--ids", nargs="*", help="Specific question IDs to run")
    parser.add_argument("--type", dest="query_type", help="Filter by query type")
    parser.add_argument("--difficulty", help="Filter by difficulty (easy/medium/hard)")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-question timeout (seconds)")
    parser.add_argument("--skip-classification", action="store_true", help="Skip streaming classification check")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    questions = load_questions(args.ids, args.query_type, args.difficulty)
    if not questions:
        logger.error("No questions matched the filters")
        return

    logger.info("Running %d questions against %s", len(questions), args.api_url)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"eval_{timestamp}.json"

    client = httpx.Client()

    # Run questions
    results = []
    for i, question in enumerate(questions, 1):
        logger.info("[%d/%d] %s", i, len(questions), question["id"])
        result = run_question(question, args.api_url, client, timeout=args.timeout)
        results.append(result)

    # Classification check via streaming endpoint
    classifications: dict[str, dict] = {}
    if not args.skip_classification:
        logger.info("Running classification checks via streaming endpoint...")
        classifications = run_classification_check(
            questions, args.api_url, client, timeout=args.timeout
        )
        # Merge classification results into main results
        for result in results:
            if result["id"] in classifications:
                cls = classifications[result["id"]]
                result["classification"] = cls
                result["scores"]["classification"] = cls["correct"]

    summary = compute_summary(results, classifications)

    report = {
        "run_timestamp": timestamp,
        "api_url": args.api_url,
        "filters": {
            "ids": args.ids,
            "query_type": args.query_type,
            "difficulty": args.difficulty,
        },
        "summary": summary,
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Results written to %s", output_path)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Evaluation complete: {summary['successful']}/{summary['total_questions']} successful")
    if summary["classification_accuracy"] is not None:
        print(f"Classification accuracy: {summary['classification_accuracy']:.0%}")
    if summary["avg_response_seconds"]:
        print(f"Avg response time: {summary['avg_response_seconds']}s")
    if summary["errors"]:
        print(f"Errors: {summary['errors']}")
    print(f"Results: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
