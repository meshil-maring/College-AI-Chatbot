"""Metrics and orchestration for the Phase 3.10 retrieval evaluation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.config import settings
from app.schemas.retrieval import RetrievalRequest
from app.services.retrieval import retrieve

SUPPORTED_CATEGORIES = ("direct", "multi-chunk", "distractor", "scope/filter")
REPORT_K_VALUES = (1, 3, 5, 10)
REQUIRED_CASE_FIELDS = {
    "id",
    "category",
    "query",
    "relevant_chunk_ids",
    "scope",
    "top_k_values",
}
SCOPE_FIELDS = (
    "institution_id",
    "knowledge_source_id",
    "document_id",
    "document_version_id",
    "processing_run_id",
    "model_name",
)


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate the JSONL evaluation dataset."""
    dataset_path = Path(path)
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with dataset_path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}") from exc
            _validate_case(case, line_number, seen_ids)
            cases.append(case)
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases


def _validate_case(case: Any, line_number: int, seen_ids: set[str]) -> None:
    if not isinstance(case, dict):
        raise ValueError(f"Dataset line {line_number} must contain an object")
    missing = REQUIRED_CASE_FIELDS - case.keys()
    if missing:
        raise ValueError(f"Dataset line {line_number} is missing: {sorted(missing)}")
    case_id = case["id"]
    if not isinstance(case_id, str) or not case_id:
        raise ValueError(f"Dataset line {line_number} has an invalid id")
    if case_id in seen_ids:
        raise ValueError(f"Duplicate case id: {case_id}")
    seen_ids.add(case_id)
    if case["category"] not in (*SUPPORTED_CATEGORIES, "unsupported"):
        raise ValueError(f"Dataset line {line_number} has an invalid category")
    if not isinstance(case["query"], str) or not case["query"].strip():
        raise ValueError(f"Dataset line {line_number} has an invalid query")
    if not isinstance(case["scope"], dict) or not any(
        case["scope"].get(field) is not None for field in SCOPE_FIELDS
    ):
        raise ValueError(f"Dataset line {line_number} must contain a retrieval scope")
    if not isinstance(case["relevant_chunk_ids"], list) or any(
        not isinstance(chunk_id, str) for chunk_id in case["relevant_chunk_ids"]
    ):
        raise ValueError(f"Dataset line {line_number} has invalid relevant_chunk_ids")
    if case["category"] == "unsupported" and case["relevant_chunk_ids"]:
        raise ValueError(f"Unsupported case {case_id} must have no relevant chunks")
    if not isinstance(case["top_k_values"], list) or not case["top_k_values"]:
        raise ValueError(f"Dataset line {line_number} has invalid top_k_values")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in case["top_k_values"]):
        raise ValueError(f"Dataset line {line_number} has invalid top_k_values")


def calculate_case_metrics(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str],
    top_k: int,
) -> dict[str, Any]:
    """Calculate one case's metrics at one cutoff."""
    retrieved = retrieved_chunk_ids[:top_k]
    relevant = set(relevant_chunk_ids)
    relevant_retrieved = [chunk_id for chunk_id in retrieved if chunk_id in relevant]
    first_rank = next(
        (rank for rank, chunk_id in enumerate(retrieved, start=1) if chunk_id in relevant),
        None,
    )
    supported = bool(relevant)
    return {
        "top_k": top_k,
        "retrieved_count": len(retrieved),
        "relevant_retrieved_count": len(relevant_retrieved),
        "recall": len(relevant_retrieved) / len(relevant) if supported else None,
        "precision": len(relevant_retrieved) / len(retrieved) if retrieved else 0.0,
        "hit": bool(relevant_retrieved) if supported else None,
        "first_relevant_rank": first_rank,
        "reciprocal_rank": 1 / first_rank if first_rank and supported else None,
        "zero_result": not retrieved,
    }


def aggregate_metrics(case_results: list[dict[str, Any]], *, supported_only: bool = True) -> dict[str, Any]:
    """Aggregate per-case cutoff metrics by arithmetic mean."""
    selected = [
        result
        for result in case_results
        if not supported_only or result["category"] != "unsupported"
    ]
    metrics: dict[str, Any] = {}
    for top_k in REPORT_K_VALUES:
        cutoff_results = [result["metrics"][str(top_k)] for result in selected]
        metrics[f"recall@{top_k}"] = _mean(item["recall"] for item in cutoff_results)
        metrics[f"precision@{top_k}"] = _mean(item["precision"] for item in cutoff_results)
        metrics[f"hit_rate@{top_k}"] = _mean(item["hit"] for item in cutoff_results)
    supported_ranks = [
        result["metrics"]["10"]["reciprocal_rank"]
        for result in selected
        if result["metrics"]["10"]["reciprocal_rank"] is not None
    ]
    metrics["mrr"] = _mean(supported_ranks)
    metrics["zero_result_rate"] = _mean(
        result["metrics"]["10"]["zero_result"] for result in selected
    )
    return metrics


def _mean(values: Any) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def scope_filter_result(case: dict[str, Any], retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    """Report observed scope violations without conflating relevance errors."""
    scope = case["scope"]
    checked_fields: list[str] = []
    unverifiable_fields: list[str] = []
    violations: list[dict[str, Any]] = []
    for field in SCOPE_FIELDS:
        if scope.get(field) is None:
            continue
        if not all(field in result for result in retrieved):
            unverifiable_fields.append(field)
            continue
        checked_fields.append(field)
        for result in retrieved:
            if str(result[field]) != str(scope[field]):
                violations.append({"chunk_id": result["chunk_id"], "field": field})
    return {
        "expected_relevant_chunk_ids": case["relevant_chunk_ids"],
        "retrieved_chunk_ids": [result["chunk_id"] for result in retrieved],
        "violating_results": violations,
        "checked_fields": checked_fields,
        "unverifiable_fields": unverifiable_fields,
        "filter_correct": not violations,
        "verification_status": "verified" if not unverifiable_fields else "partial",
    }


def evaluate_dataset(
    cases: list[dict[str, Any]],
    retrieve_case: Callable[[dict[str, Any], int], list[dict[str, Any]]] | None = None,
    *,
    evaluation_timestamp: str | None = None,
) -> dict[str, Any]:
    """Run the real retrieval pipeline and return a deterministic report structure."""
    retrieve_case = retrieve_case or _retrieve_case
    per_case: list[dict[str, Any]] = []
    scope_results: list[dict[str, Any]] = []
    unsupported_results: list[dict[str, Any]] = []
    for case in cases:
        max_top_k = max(case["top_k_values"])
        retrieved = retrieve_case(case, max_top_k)
        normalized = [_normalize_result(result, rank) for rank, result in enumerate(retrieved, 1)]
        chunk_ids = [result["chunk_id"] for result in normalized]
        case_result = {
            "case_id": case["id"],
            "category": case["category"],
            "query": case["query"],
            "requested_top_k": case["top_k_values"],
            "gold_relevant_chunk_ids": case["relevant_chunk_ids"],
            "retrieved_chunk_ids": chunk_ids,
            "retrieved_results": normalized,
            "metrics": {
                str(top_k): calculate_case_metrics(chunk_ids, case["relevant_chunk_ids"], top_k)
                for top_k in REPORT_K_VALUES
            },
            "scope": case["scope"],
        }
        if case["category"] == "scope/filter":
            case_result["scope_filter"] = scope_filter_result(case, normalized)
            scope_results.append(case_result["scope_filter"] | {"case_id": case["id"]})
        if case["category"] == "unsupported":
            unsupported_results.append({
                "case_id": case["id"],
                "zero_result": not normalized,
                "retrieved_chunk_ids": chunk_ids,
            })
        per_case.append(case_result)

    categories = {"all_supported": [result for result in per_case if result["category"] != "unsupported"]}
    for category in (*SUPPORTED_CATEGORIES, "unsupported"):
        categories[category] = [result for result in per_case if result["category"] == category]
    category_metrics = {
        category: (
            aggregate_metrics(category_cases, supported_only=category != "unsupported")
            if category_cases and category != "unsupported"
            else {metric: None for metric in _metric_names()}
        )
        for category, category_cases in categories.items()
    }
    return {
        "metadata": {
            "dataset_path": None,
            "evaluation_timestamp": evaluation_timestamp or datetime.now(UTC).isoformat(),
            "embedding_model": settings.embedding_model,
            "number_of_cases": len(cases),
        },
        "aggregate_metrics": aggregate_metrics(categories["all_supported"]),
        "category_metrics": category_metrics,
        "per_case_results": per_case,
        "scope_filter_results": scope_results,
        "unsupported_query_results": unsupported_results,
    }


def _metric_names() -> list[str]:
    return [f"{metric}@{top_k}" for metric in ("recall", "precision", "hit_rate") for top_k in REPORT_K_VALUES] + ["mrr", "zero_result_rate"]


def _retrieve_case(case: dict[str, Any], top_k: int) -> list[Any]:
    request = RetrievalRequest(query=case["query"], top_k=top_k, **case["scope"])
    return retrieve(request).results


def _normalize_result(result: Any, rank: int) -> dict[str, Any]:
    if isinstance(result, dict):
        chunk_id = str(result["chunk_id"])
        score = result.get("similarity_score")
        metadata = result.get("metadata", {})
    else:
        chunk_id = str(result.chunk_id)
        score = result.similarity_score
        metadata = result.metadata
    normalized = {
        "rank": rank,
        "chunk_id": chunk_id,
        "similarity_score": score,
    }
    normalized.update({key: value for key, value in metadata.items() if key in SCOPE_FIELDS})
    return normalized


def write_report(report: dict[str, Any], path: str | Path) -> None:
    """Write a stable, human-inspectable JSON report."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
