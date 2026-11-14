"""Audit the frozen natural-language repository retrieval benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

EVALUATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVALUATION_DIR.parent
PROJECT_SRC = PROJECT_ROOT / "src"
DEFAULT_BENCHMARK = (
    EVALUATION_DIR
    / "benchmark"
    / "ai_labeled_intent_benchmark.json"
)

if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from reposnipy_nl.retrieval import DEFAULT_REQUIREMENT_WEIGHTS  # noqa: E402

EXPECTED_SHA256 = (
    "f1f2c11371210b07d7a15c1c72896d76efb73fefed263418d36f53d5879dad0b"
)
EXPECTED_COUNTS = {
    "intent_count": 40,
    "query_count": 80,
    "candidate_rows": 2706,
    "fetched_readmes": 1182,
}
EXPECTED_SPLITS = {
    "query": {"train": 40, "validation": 20, "test": 20},
    "candidate": {"train": 1369, "validation": 678, "test": 659},
}
EXPECTED_LANGUAGES = {"zh": 1410, "en": 1296}
METRICS = (
    "nDCG@10",
    "MRR@10_strict",
    "Hit@10_strict",
    "P@10_strict",
)
METRIC_TOLERANCE = 1e-6


def require(condition: bool, message: str) -> None:
    """Raise a concise validation error."""

    if not condition:
        raise RuntimeError(message)


def close_enough(actual: float, expected: float) -> bool:
    return abs(float(actual) - float(expected)) <= METRIC_TOLERANCE


def candidate_score(candidate: dict[str, Any], readme_weight: float) -> float:
    """Reproduce coverage-aware README/docstring fusion for one candidate."""

    weights = {
        "readme": readme_weight,
        "doc": 1.0 - readme_weight,
    }
    score_keys = {
        "readme": "readme_dense",
        "doc": "doc_dense",
    }
    available_keys = {
        "readme": "readme_available",
        "doc": "doc_available",
    }
    method_scores = candidate.get("method_scores") or {}

    components: list[tuple[float, float]] = []
    for channel, weight in weights.items():
        score = method_scores.get(score_keys[channel])
        if candidate.get(available_keys[channel]) and score is not None:
            components.append((weight, float(score)))

    available_weight = sum(weight for weight, _ in components)
    if available_weight == 0:
        return -math.inf
    fused = sum(weight * score for weight, score in components)
    return fused / available_weight


def ranked_candidates(
    candidates: list[dict[str, Any]],
    readme_weight: float,
) -> list[dict[str, Any]]:
    """Return a deterministic closed-pool ranking."""

    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate_score(candidate, readme_weight),
            candidate["repo"],
        ),
    )


def metrics_for_query(
    candidates: list[dict[str, Any]],
    readme_weight: float,
) -> dict[str, float]:
    """Compute core strict metrics for one query at one fusion weight."""

    ranked = ranked_candidates(candidates, readme_weight)
    top = ranked[:10]
    labels = [int(candidate["label"]) for candidate in top]

    dcg = sum(
        (2**label - 1) / math.log2(rank + 2)
        for rank, label in enumerate(labels)
    )
    ideal_labels = sorted(
        (int(candidate["label"]) for candidate in ranked),
        reverse=True,
    )[:10]
    idcg = sum(
        (2**label - 1) / math.log2(rank + 2)
        for rank, label in enumerate(ideal_labels)
    )
    ndcg = dcg / idcg if idcg else 0.0

    reciprocal_rank = 0.0
    for rank, label in enumerate(labels, start=1):
        if label == 2:
            reciprocal_rank = 1.0 / rank
            break

    return {
        "nDCG@10": ndcg,
        "MRR@10_strict": reciprocal_rank,
        "Hit@10_strict": 1.0 if any(label == 2 for label in labels) else 0.0,
        "P@10_strict": sum(label == 2 for label in labels) / 10.0,
    }


def split_metrics(
    queries_by_split: dict[str, list[str]],
    candidates_by_query: dict[str, list[dict[str, Any]]],
    split: str,
    readme_weight: float,
) -> dict[str, Any]:
    """Average per-query metrics over one frozen split."""

    query_ids = queries_by_split[split]
    per_query = [
        metrics_for_query(candidates_by_query[query_id], readme_weight)
        for query_id in query_ids
    ]
    require(bool(per_query), f"split {split} has no queries")
    return {
        "n_queries": len(query_ids),
        **{
            metric: round(
                sum(values[metric] for values in per_query) / len(per_query),
                6,
            )
            for metric in METRICS
        },
    }


def validate_benchmark(benchmark: dict[str, Any]) -> dict[str, Any]:
    """Validate data integrity, recompute the grid, and check production weights."""

    require(
        benchmark.get("status") == "HUMAN_VERIFIED_AI_LABELS",
        "benchmark is not marked as human-verified AI labels",
    )
    require(
        benchmark.get("valid_as_human_gold") is True,
        "benchmark is not marked valid as human gold",
    )

    dataset = benchmark["dataset"]
    queries = benchmark["queries"]
    candidates = benchmark["candidates"]
    require(
        len({query["intent_id"] for query in queries})
        == EXPECTED_COUNTS["intent_count"],
        "intent count mismatch",
    )
    require(
        len(queries) == EXPECTED_COUNTS["query_count"],
        "query count mismatch",
    )
    require(
        len(candidates) == EXPECTED_COUNTS["candidate_rows"],
        "candidate count mismatch",
    )
    require(
        dataset["corpus"]["fetched_readmes"]
        == EXPECTED_COUNTS["fetched_readmes"],
        "README corpus count mismatch",
    )

    query_lookup = {query["query_id"]: query for query in queries}
    require(
        len(query_lookup) == len(queries),
        "duplicate query identifiers",
    )
    queries_by_split: dict[str, list[str]] = defaultdict(list)
    for query in queries:
        queries_by_split[query["split"]].append(query["query_id"])
    query_split_counts = {
        split: len(ids)
        for split, ids in queries_by_split.items()
    }
    require(
        query_split_counts == EXPECTED_SPLITS["query"],
        f"query split mismatch: {query_split_counts}",
    )

    candidates_by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    candidate_splits: list[str] = []
    for candidate in candidates:
        query_id = candidate["query_id"]
        require(query_id in query_lookup, f"unknown query: {query_id}")
        require(
            int(candidate["label"]) in (0, 1, 2),
            f"invalid label for {query_id}/{candidate['repo']}",
        )
        require(
            candidate["split"] == query_lookup[query_id]["split"],
            f"split mismatch for {query_id}/{candidate['repo']}",
        )
        key = (query_id, candidate["repo"])
        require(key not in seen, f"duplicate candidate: {key}")
        seen.add(key)
        candidates_by_query[query_id].append(candidate)
        candidate_splits.append(candidate["split"])

    candidate_split_counts = dict(Counter(candidate_splits))
    require(
        candidate_split_counts == EXPECTED_SPLITS["candidate"],
        f"candidate split mismatch: {candidate_split_counts}",
    )
    language_counts = dict(Counter(candidate["language"] for candidate in candidates))
    require(
        language_counts == EXPECTED_LANGUAGES,
        f"language count mismatch: {language_counts}",
    )

    weight_experiment = benchmark["weight_experiment"]
    grid = weight_experiment["grid"]
    require(len(grid) == 101, "weight grid must contain 101 points")
    require(
        [round(float(row["readme_weight"]), 2) for row in grid]
        == [index / 100 for index in range(101)],
        "weight grid is not README 0.00..1.00 by 0.01",
    )
    require(
        weight_experiment["selection_split"] == "validation",
        "weight selection split must be validation",
    )

    verified_rows = 0
    for row in grid:
        readme_weight = float(row["readme_weight"])
        require(
            close_enough(
                readme_weight + float(row["doc_weight"]),
                1.0,
            ),
            "grid weights do not sum to one",
        )
        for split in ("train", "validation", "test"):
            computed = split_metrics(
                queries_by_split,
                candidates_by_query,
                split,
                readme_weight,
            )
            for metric in METRICS:
                require(
                    close_enough(computed[metric], row[split][metric]),
                    (
                        f"grid mismatch at README {readme_weight:.2f}, "
                        f"{split} {metric}: "
                        f"{computed[metric]} != {row[split][metric]}"
                    ),
                )
        verified_rows += 1

    selected = weight_experiment["selected"]
    selected_row = next(
        row
        for row in grid
        if close_enough(
            row["readme_weight"],
            selected["readme_weight"],
        )
    )
    for split in ("train", "validation", "test"):
        for metric in METRICS:
            require(
                close_enough(selected[split][metric], selected_row[split][metric]),
                f"selected block mismatch for {split} {metric}",
            )
        require(
            close_enough(
                selected[split]["Recall@10_strict"],
                selected_row[split]["Recall@10_strict"],
            ),
            f"frozen recall mismatch for {split}",
        )

    best_validation = max(
        grid,
        key=lambda row: (
            row["validation_nDCG_bootstrap_lcb95"],
            row["validation"]["nDCG@10"],
            row["validation"]["MRR@10_strict"],
            row["validation"]["Hit@10_strict"],
            -abs(row["readme_weight"] - row["doc_weight"]),
        ),
    )
    require(
        close_enough(
            best_validation["readme_weight"],
            selected["readme_weight"],
        ),
        "selected ratio is not the validation optimum",
    )

    best_test = max(
        grid,
        key=lambda row: (
            row["test"]["nDCG@10"],
            -abs(row["readme_weight"] - row["doc_weight"]),
        ),
    )
    diagnostic = weight_experiment["best_test_diagnostic_only"]
    require(
        close_enough(
            best_test["readme_weight"],
            diagnostic["readme_weight"],
        ),
        "test-only diagnostic weight mismatch",
    )
    require(
        not close_enough(
            diagnostic["readme_weight"],
            selected["readme_weight"],
        ),
        "test-only diagnostic must not equal the frozen selection",
    )

    configured = DEFAULT_REQUIREMENT_WEIGHTS["blend"]
    require(
        close_enough(configured["readme"], selected["readme_weight"]),
        "production README weight does not match the frozen selection",
    )
    require(
        close_enough(configured["doc"], selected["doc_weight"]),
        "production docstring weight does not match the frozen selection",
    )

    return {
        "dataset": {
            "intents": EXPECTED_COUNTS["intent_count"],
            "queries": EXPECTED_COUNTS["query_count"],
            "candidate_rows": EXPECTED_COUNTS["candidate_rows"],
            "fetched_readmes": EXPECTED_COUNTS["fetched_readmes"],
            "query_splits": EXPECTED_SPLITS["query"],
            "candidate_splits": EXPECTED_SPLITS["candidate"],
            "candidate_languages": EXPECTED_LANGUAGES,
        },
        "weight_grid_points": len(grid),
        "weight_grid_metric_values_recomputed": verified_rows * 3 * len(METRICS),
        "selection_split": "validation",
        "selected": {
            "readme": selected["readme_weight"],
            "doc": selected["doc_weight"],
            "validation_bootstrap_lcb95": selected[
                "validation_nDCG_bootstrap_lcb95"
            ],
            "validation": {
                metric: selected["validation"][metric]
                for metric in METRICS
            },
            "test": {
                metric: selected["test"][metric]
                for metric in METRICS
            },
        },
        "frozen_recall": {
            "validation": selected["validation"]["Recall@10_strict"],
            "test": selected["test"]["Recall@10_strict"],
            "usage": "Preserved from the frozen benchmark; not used for weight selection.",
        },
        "test_only_diagnostic": {
            "readme": diagnostic["readme_weight"],
            "doc": diagnostic["doc_weight"],
            "test_nDCG@10": diagnostic["test"]["nDCG@10"],
            "usage": "Diagnostic only; never used to change production weights.",
        },
        "production_weights": {
            "readme": configured["readme"],
            "doc": configured["doc"],
        },
    }


def run_audit(benchmark_path: Path) -> dict[str, Any]:
    started = time.time()
    encoded = benchmark_path.read_bytes()
    actual_sha256 = hashlib.sha256(encoded).hexdigest()
    require(
        actual_sha256 == EXPECTED_SHA256,
        f"benchmark checksum mismatch: {actual_sha256}",
    )
    benchmark = json.loads(encoded.decode("utf-8"))
    result = validate_benchmark(benchmark)
    return {
        "schema_version": "reposnipy-nl-benchmark-audit.v1",
        "status": "passed",
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.time() - started, 3),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "benchmark": {
            "path": benchmark_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": actual_sha256,
            "status": benchmark["status"],
            "valid_as_human_gold": benchmark["valid_as_human_gold"],
        },
        **result,
        "scope": (
            "Closed-pool reranking over the benchmark candidate union. "
            "These results do not measure full-index recall."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and recompute the frozen RepoSnipy-NL benchmark."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=DEFAULT_BENCHMARK,
        help="Path to the frozen benchmark JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON audit result.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_audit(args.benchmark.resolve())
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
