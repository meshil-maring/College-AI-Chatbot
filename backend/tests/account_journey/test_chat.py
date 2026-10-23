from .support import (
    AppError,
    FOREIGN_TENANT,
    INSTITUTION_A,
    _active_institution_authorization,
    patch,
    pytest,
)


def test_retrieval_requires_an_explicit_scope():
    from pydantic import ValidationError

    from app.schemas.knowledge.retrieval import RetrievalRequest

    with pytest.raises(ValidationError):
        RetrievalRequest(query="What time does the library close?")
    with pytest.raises(ValidationError):
        RetrievalRequest(query="   ", institution_id=INSTITUTION_A)


def test_retrieval_passes_the_requested_tenant_to_the_vector_search():
    from app.schemas.knowledge.retrieval import RetrievalRequest
    from app.services.knowledge import retrieval as retrieval_service

    with (
        patch.object(retrieval_service, "embed_query", return_value=[0.0] * 1536),
        patch.object(retrieval_service, "search_chunks", return_value=[]) as search,
    ):
        response = retrieval_service.retrieve(
            RetrievalRequest(
                query="library hours", institution_id=INSTITUTION_A, top_k=4
            )
        )
    assert response.results == []
    assert search.call_args.kwargs["institution_id"] == INSTITUTION_A


def test_retrieval_for_a_foreign_tenant_returns_no_rows():
    from app.schemas.knowledge.retrieval import RetrievalRequest
    from app.services.knowledge import retrieval as retrieval_service

    with (
        patch.object(retrieval_service, "embed_query", return_value=[0.0] * 1536),
        patch.object(retrieval_service, "search_chunks", return_value=[]) as search,
    ):
        response = retrieval_service.retrieve(
            RetrievalRequest(query="library hours", institution_id=FOREIGN_TENANT)
        )
    assert response.results == []
    assert search.call_args.kwargs["institution_id"] == FOREIGN_TENANT


def test_retrieval_failure_is_reported_without_leaking_internals():
    from app.schemas.knowledge.retrieval import RetrievalRequest
    from app.services.knowledge import retrieval as retrieval_service

    with (
        patch.object(retrieval_service, "embed_query", return_value=[0.0] * 1536),
        patch.object(
            retrieval_service,
            "search_chunks",
            side_effect=AppError("db exploded at table knowledge_chunks", code="X"),
        ),
    ):
        with pytest.raises(AppError) as excinfo:
            retrieval_service.retrieve(
                RetrievalRequest(query="library hours", institution_id=INSTITUTION_A)
            )
    assert excinfo.value.code == "RETRIEVAL_FAILED"
    assert "db exploded" not in (excinfo.value.message or "")
