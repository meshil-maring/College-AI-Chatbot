"""Citations: reference validation."""

from .support import (
    CHUNK_A_ID,
    CHUNK_B_ID,
    GenerationProvider,
    GenerationResult,
    MagicMock,
    UUID,
    _chat_request,
    _mock_client,
    _process,
    _sync_background_persistence,
)


def test_single_valid_citation_is_persisted():
    """Answer containing [Retrieved chunk <UUID>] creates exactly one message_citations row."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.message_id is not None
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # Verify 7 inserts: conversation + user + assistant + ai_response + retrieval_op + chunks + 1 citation
    assert mc.table().insert().execute.call_count == 7


def test_multiple_valid_citations_are_persisted():
    """Answer referencing two retrieved chunks creates two message_citations rows."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}] and [Retrieved chunk {CHUNK_B_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert len(response.source_references) == 2
    ref_ids = {r.chunk_id for r in response.source_references}
    assert ref_ids == {UUID(CHUNK_A_ID), UUID(CHUNK_B_ID)}

    # 7 inserts: conversation + user + assistant + ai_response + retrieval_op + chunks_batch + citations_batch
    assert mc.table().insert().execute.call_count == 7


def test_no_explicit_citation_produces_zero_citations():
    """Successful answer without chunk references creates zero message_citations rows."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="The admission process is straightforward.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.message_id is not None
    assert response.source_references == []

    # 6 inserts: ... + retrieval_op + chunks (NO citation insert)
    assert mc.table().insert().execute.call_count == 6


def test_invalid_uuid_in_answer_does_not_create_citation():
    """[Retrieved chunk not-a-valid-uuid] does not create a citation."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="See [Retrieved chunk not-a-valid-uuid].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.source_references == []

    # 6 inserts: no citation created for invalid UUID
    assert mc.table().insert().execute.call_count == 6


def test_valid_uuid_not_in_retrieved_chunks_does_not_create_citation():
    """A valid UUID not in the retrieved set does not create a citation."""
    non_retrieved_id = "50000000-0000-0000-0000-000000000001"
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {non_retrieved_id}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.source_references == []

    # 6 inserts: no citation for non-retrieved chunk
    assert mc.table().insert().execute.call_count == 6


def test_duplicate_reference_does_not_create_duplicate_citations():
    """Referencing the same chunk twice creates only one citation (deduplicated by extract logic)."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=(
            f"First [Retrieved chunk {CHUNK_A_ID}] "
            f"and again [Retrieved chunk {CHUNK_A_ID}]."
        ),
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    # _extract_source_references uses a set for referenced_ids, so duplicates are collapsed
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # 7 inserts: ... + retrieval_op + chunks + 1 citation (not 2)
    assert mc.table().insert().execute.call_count == 7
