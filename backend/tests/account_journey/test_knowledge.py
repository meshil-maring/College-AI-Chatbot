from .support import (
    KNOWLEDGE_SOURCE_ID,
    MagicMock,
    PROCESSING_RUN_ID,
    _active_institution_authorization,
)


def test_processing_run_query_documents_the_corrected_tenant_resolution():
    """Defect 1 â€” the fix rationale is pinned in the repository docstring."""
    from app.repositories.knowledge import ingestion as ingestion_repo

    documented = ingestion_repo.get_processing_run_with_version.__doc__ or ""
    assert "documents(knowledge_source_id)" in documented
    assert "knowledge_source_id" in documented


def test_processing_run_tenant_is_hoisted_from_the_document_row():
    """Defect 1 â€” the tenant must come from ``documents``, not ``document_versions``."""
    run_row = {
        "processing_run_id": PROCESSING_RUN_ID,
        "status": "queued",
        "document_version_id": "30000000-0000-0000-0000-000000000931",
        "document_versions": {
            "document_version_id": "30000000-0000-0000-0000-000000000931",
            "storage_bucket": "college-ai-knowledge",
            "storage_object_key": "tenant/key",
            "file_type": "txt",
            "documents": {"knowledge_source_id": KNOWLEDGE_SOURCE_ID},
        },
    }
    response = MagicMock()
    response.data = run_row
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = response
    fake_client = MagicMock()
    fake_client.table.return_value = chain

    from app.repositories.knowledge.ingestion import get_processing_run_with_version

    run = get_processing_run_with_version(fake_client, PROCESSING_RUN_ID)
    assert run["document_versions"]["knowledge_source_id"] == KNOWLEDGE_SOURCE_ID
    selected = chain.select.call_args.args[0]
    assert "documents(knowledge_source_id)" in selected
    assert "file_type, knowledge_source_id)" not in selected
