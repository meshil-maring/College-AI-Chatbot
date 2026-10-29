"""Responses: source titles."""

from .support import (
    CHUNK_A_ID,
    CHUNK_A_TEXT,
    MagicMock,
    SourceReference,
    UUID,
    _build_structured_sources,
    _enrich_source_titles,
    _retrieval_chunks,
)


def test_source_title_enrichment_via_provenance_chain():
    """Enrichment resolves source_title from knowledge_sources.title via provenance chain."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results
    structured = _build_structured_sources(source_refs, chunks)

    # The fast path issues ONE embedded PostgREST foreign-key query
    # (knowledge_chunks -> document_processing_runs -> document_versions ->
    # documents -> knowledge_sources.title).
    mock_client = MagicMock()
    mock_client.table("knowledge_chunks").select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {
                "chunk_id": CHUNK_A_ID,
                "document_processing_runs": [
                    {
                        "document_versions": [
                            {
                                "documents": [
                                    {
                                        "knowledge_sources": [
                                            {"title": "Attendance Regulations"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
            }
        ]
    )

    _enrich_source_titles(mock_client, structured)

    assert structured[0].source_title == "Attendance Regulations"


def test_source_title_enrichment_to_one_relationship_dict_shape():
    """PostgREST returns to-one embedded members as dicts; titles must still resolve."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results
    structured = _build_structured_sources(source_refs, chunks)

    mock_client = MagicMock()
    # Production PostgREST shape: each embedded level is an OBJECT (to-one FK),
    # not an array.
    mock_client.table("knowledge_chunks").select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {
                "chunk_id": CHUNK_A_ID,
                "document_processing_runs": {
                    "document_versions": {
                        "documents": {
                            "knowledge_sources": {"title": "Hostel Fee Structure"}
                        }
                    }
                },
            }
        ]
    )

    _enrich_source_titles(mock_client, structured)

    assert structured[0].source_title == "Hostel Fee Structure"


def test_source_title_enrichment_falls_back_to_sequential_chain():
    """When the embedded provenance query fails, the sequential chain is used."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results
    structured = _build_structured_sources(source_refs, chunks)

    # The embedded fast path returns rows WITHOUT nested provenance, so no
    # titles are resolvable and the code falls through to the sequential
    # 5-query chain. Each table's mock is configured by name so the chain can
    # resolve the full path knowledge_chunks -> ... -> knowledge_sources.
    seed = {
        "knowledge_chunks": MagicMock(
            data=[{"chunk_id": CHUNK_A_ID, "processing_run_id": "run-001"}]
        ),
        "document_processing_runs": MagicMock(
            data=[{"processing_run_id": "run-001", "document_version_id": "ver-001"}]
        ),
        "document_versions": MagicMock(
            data=[{"document_version_id": "ver-001", "document_id": "doc-001"}]
        ),
        "documents": MagicMock(
            data=[{"document_id": "doc-001", "knowledge_source_id": "ks-001"}]
        ),
        "knowledge_sources": MagicMock(
            data=[{"knowledge_source_id": "ks-001", "title": "Attendance Regulations"}]
        ),
    }

    def _table(table_name: str) -> MagicMock:
        table_mock = MagicMock()
        table_mock.select.return_value.in_.return_value.execute.return_value = seed[
            table_name
        ]
        return table_mock

    mock_client = MagicMock()
    mock_client.table.side_effect = _table

    _enrich_source_titles(mock_client, structured)

    assert structured[0].source_title == "Attendance Regulations"
