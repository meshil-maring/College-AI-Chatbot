import json

import pytest

from evaluation.evaluator import (
    aggregate_metrics,
    calculate_case_metrics,
    evaluate_dataset,
    load_dataset,
    scope_filter_result,
)


def test_recall_calculation():
    metrics = calculate_case_metrics(["a", "b", "c"], ["a", "c"], 3)
    assert metrics["recall"] == 1.0


def test_precision_calculation_uses_actual_result_count():
    metrics = calculate_case_metrics(["a", "x"], ["a"], 5)
    assert metrics["precision"] == 0.5


def test_hit_rate_calculation():
    assert calculate_case_metrics(["x", "a"], ["a"], 1)["hit"] is False
    assert calculate_case_metrics(["x", "a"], ["a"], 2)["hit"] is True


def test_mrr_calculation():
    metrics = calculate_case_metrics(["x", "a"], ["a"], 10)
    assert metrics["reciprocal_rank"] == 0.5


def test_zero_result_handling():
    metrics = calculate_case_metrics([], ["a"], 3)
    assert metrics["zero_result"] is True
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0


def test_unsupported_query_handling():
    metrics = calculate_case_metrics(["a"], [], 3)
    assert metrics["recall"] is None
    assert metrics["hit"] is None
    assert metrics["reciprocal_rank"] is None


def test_multiple_relevant_chunks():
    metrics = calculate_case_metrics(["a", "b", "x"], ["a", "b"], 3)
    assert metrics["relevant_retrieved_count"] == 2
    assert metrics["recall"] == 1.0


def test_top_k_smaller_than_available_results():
    metrics = calculate_case_metrics(["a", "x", "b"], ["a", "b"], 1)
    assert metrics["retrieved_count"] == 1
    assert metrics["recall"] == 0.5


def test_scope_filter_evaluation_distinguishes_violation():
    case = {
        "relevant_chunk_ids": ["a"],
        "scope": {"document_id": "doc-1", "model_name": "model-1"},
    }
    result = scope_filter_result(
        case,
        [{"chunk_id": "a", "document_id": "doc-2", "model_name": "model-1"}],
    )
    assert result["filter_correct"] is False
    assert result["violating_results"] == [{"chunk_id": "a", "field": "document_id"}]


def test_dataset_loading_and_validation(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "category": "direct",
                "query": "question",
                "relevant_chunk_ids": ["chunk-1"],
                "scope": {"model_name": "model"},
                "top_k_values": [1, 3],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert load_dataset(path)[0]["id"] == "case-1"

    path.write_text("{bad json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_dataset(path)


def test_deterministic_result_structure():
    case = {
        "id": "case-1",
        "category": "direct",
        "query": "question",
        "relevant_chunk_ids": ["chunk-1"],
        "scope": {"model_name": "model"},
        "top_k_values": [1, 3, 5, 10],
    }

    def retrieve_case(_case, _top_k):
        return [{"chunk_id": "chunk-1", "similarity_score": 0.9, "metadata": {}}]

    report = evaluate_dataset([case], retrieve_case, evaluation_timestamp="fixed")
    assert report["metadata"]["evaluation_timestamp"] == "fixed"
    assert list(report["per_case_results"][0]["metrics"]) == ["1", "3", "5", "10"]
    assert report["per_case_results"][0]["retrieved_results"][0]["rank"] == 1


def test_aggregate_metrics_excludes_unsupported_cases():
    supported = {
        "category": "direct",
        "metrics": {str(k): calculate_case_metrics(["a"], ["a"], k) for k in (1, 3, 5, 10)},
    }
    unsupported = {
        "category": "unsupported",
        "metrics": {str(k): calculate_case_metrics([], [], k) for k in (1, 3, 5, 10)},
    }
    aggregate = aggregate_metrics([supported, unsupported])
    assert aggregate["recall@1"] == 1.0
    assert aggregate["zero_result_rate"] == 0.0
