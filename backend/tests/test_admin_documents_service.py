"""Phase Admin-3 tests — document orchestration service.

Covers: full RAG pipeline execution on a queued run, upload orchestration,
update with create_next_document_version + stale-content purge, delete with
retrieval-content removal, and the canonical-text sync engine.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.errors import AppError
from app.schemas.ingestion import IngestResponse
from app.services import admin_documents as svc

DOC_ID = str(uuid4())
V1_ID = str(uuid4())
RUN1_ID = str(uuid4())


def _fake_file(name: str = "handbook.txt", content: bytes = b"hello"):
    class _File:
        filename = name
        content_type = "text/plain"

        async def read(self):
            return content

    return _File()


def _run_doc(versions):
    return {
        "document_id": DOC_ID,
        "knowledge_source_id": str(uuid4()),
        "versions": versions,
    }


def _version(version_id: str, number: int = 1):
    return {
        "document_version_id": version_id,
        "document_id": DOC_ID,
        "version_number": number,
        "storage_bucket": "documents",
        "storage_object_key": f"documents/{DOC_ID}/{version_id}/f.pdf",
    }


# ============================================================================
# process_run_to_retrieval
# ============================================================================


def test_process_run_executes_extraction_chunking_embedding_in_order() -> None:
    db = MagicMock()
    calls = []

    with (
        patch(
            "app.services.admin_documents.get_processing_run_with_version",
            side_effect=lambda db_, run_id: calls.append("get_run")
            or {
                "processing_run_id": run_id,
                "status": "queued",
                "document_versions": {
                    "document_version_id": V1_ID,
                    "storage_bucket": "documents",
                    "storage_object_key": "k",
                    "file_type": "pdf",
                },
            },
        ),
        patch(
            "app.services.admin_documents.update_run_status",
            side_effect=lambda *a, **k: calls.append("status"),
        ),
        patch(
            "app.services.admin_documents.get_r2_client",
            side_effect=lambda: calls.append("r2") or MagicMock(),
        ),
        patch(
            "app.services.admin_documents.download_file",
            side_effect=lambda *a: calls.append("download") or b"data",
        ),
        patch(
            "app.services.admin_documents.extract_text",
            side_effect=lambda data, ft: calls.append("extract") or "hello world",
        ),
        patch(
            "app.services.admin_documents.store_extracted_text",
            side_effect=lambda *a: calls.append("store"),
        ),
        patch(
            "app.services.admin_documents.chunk_text",
            side_effect=lambda text: calls.append("chunk")
            or [{"chunk_sequence": 0, "content_text": text, "token_count": 2}],
        ),
        patch(
            "app.services.admin_documents.insert_chunks",
            side_effect=lambda *a: calls.append("insert_chunks") or 1,
        ),
        patch(
            "app.services.admin_documents.embed_processing_run",
            side_effect=lambda run_id: calls.append("embed") or 1,
        ),
    ):
        result = svc.process_run_to_retrieval(RUN1_ID, client=db)

    assert result["status"] == "embedded"
    assert result["chunks_created"] == 1
    assert result["embeddings_created"] == 1
    order = [
        c
        for c in calls
        if c
        in ("get_run", "download", "extract", "chunk", "insert_chunks", "embed")
    ]
    assert order == [
        "get_run",
        "download",
        "extract",
        "chunk",
        "insert_chunks",
        "embed",
    ]


def test_process_run_404_when_run_missing() -> None:
    db = MagicMock()
    with patch(
        "app.services.admin_documents.get_processing_run_with_version",
        return_value=None,
    ):
        with pytest.raises(AppError) as exc:
            svc.process_run_to_retrieval(RUN1_ID, client=db)
    assert exc.value.status_code == 404


def test_process_run_409_when_not_queued() -> None:
    db = MagicMock()
    with patch(
        "app.services.admin_documents.get_processing_run_with_version",
        return_value={
            "status": "ready",
            "document_versions": {"document_version_id": V1_ID},
        },
    ):
        with pytest.raises(AppError) as exc:
            svc.process_run_to_retrieval(RUN1_ID, client=db)
    assert exc.value.status_code == 409
    assert exc.value.code == "RUN_NOT_QUEUED"


def test_process_run_rejects_empty_extraction() -> None:
    """A scanned/blank PDF must fail fast instead of an unusable KS."""
    db = MagicMock()
    with (
        patch(
            "app.services.admin_documents.get_processing_run_with_version",
            return_value={
                "processing_run_id": RUN1_ID,
                "status": "queued",
                "document_versions": {
                    "document_version_id": V1_ID,
                    "storage_bucket": "documents",
                    "storage_object_key": "k",
                    "file_type": "pdf",
                },
            },
        ),
        patch("app.services.admin_documents.update_run_status") as status_mock,
        patch("app.services.admin_documents.get_r2_client", return_value=MagicMock()),
        patch("app.services.admin_documents.download_file", return_value=b"data"),
        patch("app.services.admin_documents.extract_text", return_value="   \n  "),
        patch("app.services.admin_documents.store_extracted_text"),
        patch("app.services.admin_documents.chunk_text") as chunk_mock,
        patch("app.services.admin_documents.embed_processing_run") as embed_mock,
    ):
        with pytest.raises(AppError) as exc:
            svc.process_run_to_retrieval(RUN1_ID, db)
    assert exc.value.code == "EMPTY_EXTRACTION"
    chunk_mock.assert_not_called()
    embed_mock.assert_not_called()
    failed_calls = [
        c for c in status_mock.call_args_list if c.kwargs.get("status") == "failed"
    ]
    assert failed_calls, "run must be marked failed on empty extraction"


def test_process_run_marks_run_failed_when_embedding_fails() -> None:
    """Embedding errors must leave the run failed, not ready/embedded."""
    db = MagicMock()
    with (
        patch(
            "app.services.admin_documents.get_processing_run_with_version",
            return_value={
                "processing_run_id": RUN1_ID,
                "status": "queued",
                "document_versions": {
                    "document_version_id": V1_ID,
                    "storage_bucket": "documents",
                    "storage_object_key": "k",
                    "file_type": "txt",
                },
            },
        ),
        patch("app.services.admin_documents.update_run_status") as status_mock,
        patch("app.services.admin_documents.get_r2_client", return_value=MagicMock()),
        patch("app.services.admin_documents.store_extracted_text"),
        patch("app.services.admin_documents.download_file", return_value=b"data"),
        patch("app.services.admin_documents.extract_text", return_value="hello world"),
        patch(
            "app.services.admin_documents.chunk_text",
            return_value=[
                {"chunk_sequence": 1, "content_text": "hello world", "token_count": 3}
            ],
        ),
        patch("app.services.admin_documents.insert_chunks", return_value=1),
        patch(
            "app.services.admin_documents.embed_processing_run",
            side_effect=AppError("boom", status_code=500, code="EMBEDDING_FAILED"),
        ),
    ):
        with pytest.raises(AppError):
            svc.process_run_to_retrieval(RUN1_ID, db)
    failed_calls = [
        c for c in status_mock.call_args_list if c.kwargs.get("status") == "failed"
    ]
    assert failed_calls, "run must be marked failed on embedding error"

def test_process_run_marks_failed_on_extraction_error() -> None:
    db = MagicMock()
    with (
        patch(
            "app.services.admin_documents.get_processing_run_with_version",
            return_value={
                "status": "queued",
                "document_versions": {
                    "document_version_id": V1_ID,
                    "storage_bucket": "documents",
                    "storage_object_key": "k",
                    "file_type": "pdf",
                },
            },
        ),
        patch(
            "app.services.admin_documents.update_run_status"
        ) as status_mock,
        patch(
            "app.services.admin_documents.get_r2_client", return_value=MagicMock()
        ),
        patch(
            "app.services.admin_documents.download_file",
            side_effect=Exception("boom"),
        ),
    ):
        with pytest.raises(AppError) as exc:
            svc.process_run_to_retrieval(RUN1_ID, client=db)

    assert exc.value.code == "EXTRACTION_FAILED"
    failed_calls = [
        c for c in status_mock.call_args_list if c.kwargs.get("status") == "failed"
    ]
    assert failed_calls

def test_upload_document_delegates_to_ingest_and_processes_pipeline() -> None:
    ingest_response = IngestResponse(
        knowledge_source_id=str(uuid4()),
        document_id=DOC_ID,
        document_version_id=V1_ID,
        processing_run_id=RUN1_ID,
        storage_object_key="k",
        status="queued",
    )
    with (
        patch(
            "app.services.admin_documents.ingest_document",
            new=AsyncMock(return_value=ingest_response),
        ),
        patch(
            "app.services.admin_documents.process_run_to_retrieval",
            return_value={"status": "embedded"},
        ) as process_mock,
    ):
        result = asyncio.run(
            svc.upload_document(
                file=_fake_file(), knowledge_source_id="ks", user_id="u1", auto_process=True
            )
        )
        assert result["document_id"] == DOC_ID
        assert result["pipeline"]["status"] == "embedded"
        process_mock.assert_called_once_with(RUN1_ID)

        process_mock.reset_mock()
        result = asyncio.run(
            svc.upload_document(
                file=_fake_file(), knowledge_source_id="ks", user_id="u1", auto_process=False
            )
        )
        assert "pipeline" not in result
        process_mock.assert_not_called()

def test_update_document_uses_next_version_helper_and_purges_stale_content() -> None:
    db = MagicMock()
    doc = _run_doc([_version(V1_ID, 1)])
    with (
        patch("app.services.admin_documents.get_admin_client", return_value=db),
        patch(
            "app.services.admin_documents.get_document_with_versions",
            return_value=doc,
        ),
        patch(
            "app.services.admin_documents.purge_version_retrieval_content",
            return_value=[RUN1_ID],
        ) as purge_mock,
        patch(
            "app.services.admin_documents.get_r2_client", return_value=MagicMock()
        ),
        patch("app.services.admin_documents.upload_file") as upload_mock,
        patch(
            "app.services.admin_documents.create_next_document_version"
        ) as next_version_mock,
        patch(
            "app.services.admin_documents.create_processing_run",
            return_value={"processing_run_id": RUN1_ID},
        ),
        patch(
            "app.services.admin_documents.process_run_to_retrieval",
            return_value={"chunks_created": 3, "status": "embedded"},
        ) as process_mock,
        patch(
            "app.services.admin_documents.update_document_version_lifecycle"
        ) as lifecycle_mock,
    ):
        next_version_mock.return_value = {
            "document_version_id": str(uuid4()),
            "version_number": 2,
            "supersedes_version_id": V1_ID,
        }

        result = asyncio.run(
            svc.update_document(
                file=_fake_file(), document_id=DOC_ID, user_id="u1", auto_process=True
            )
        )

    assert result["version_number"] == 2
    assert result["supersedes_version_id"] == V1_ID
    # Superseded version's retrieval content is purged before the new version.
    purge_mock.assert_called_once_with(db, [V1_ID])
    # New version registered through the Admin-2 helper with the correct doc.
    payload = next_version_mock.call_args.args[1]
    assert payload.document_id == UUID(DOC_ID)
    assert next_version_mock.call_args.args[2] == "u1"
    upload_mock.assert_called_once()
    process_mock.assert_called_once()
    lifecycle_mock.assert_called_once()


def test_update_document_404_when_document_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_documents.get_admin_client", return_value=db),
        patch(
            "app.services.admin_documents.get_document_with_versions",
            return_value=None,
        ),
    ):
        with pytest.raises(AppError) as exc:
            asyncio.run(
                svc.update_document(
                    file=_fake_file(), document_id=DOC_ID, user_id="u1"
                )
            )
    assert exc.value.status_code == 404


def test_delete_document_removes_retrieval_content_rows_and_storage() -> None:
    db = MagicMock()
    doc = _run_doc([_version(V1_ID, 1)])
    with (
        patch("app.services.admin_documents.get_admin_client", return_value=db),
        patch(
            "app.services.admin_documents.get_document_with_versions",
            return_value=doc,
        ),
        patch(
            "app.services.admin_documents.purge_version_retrieval_content",
            return_value=[RUN1_ID],
        ) as purge_mock,
        patch(
            "app.services.admin_documents.get_r2_client", return_value=MagicMock()
        ),
        patch("app.services.admin_documents.delete_file") as delete_file_mock,
    ):
        result = svc.delete_document(DOC_ID, client=db)

    assert result["deleted"] is True
    purge_mock.assert_called_once_with(db, [V1_ID])
    tables = [call.args[0] for call in db.table.call_args_list]
    assert "document_versions" in tables
    assert "documents" in tables
    delete_file_mock.assert_called_once()


def test_delete_document_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_documents.get_admin_client", return_value=db),
        patch(
            "app.services.admin_documents.get_document_with_versions",
            return_value=None,
        ),
    ):
        with pytest.raises(AppError) as exc:
            svc.delete_document(DOC_ID, client=db)
    assert exc.value.status_code == 404


def test_purge_version_retrieval_content_removes_embeddings_chunks_runs() -> None:
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.execute
    ).return_value = MagicMock(data=[{"processing_run_id": RUN1_ID}])
    with (
        patch(
            "app.services.admin_documents.delete_embeddings_for_run"
        ) as emb_mock,
        patch("app.services.admin_documents.delete_chunks_for_run") as chunks_mock,
    ):
        run_ids = svc.purge_version_retrieval_content(db, [V1_ID])

    assert run_ids == [RUN1_ID]
    emb_mock.assert_called_once()
    chunks_mock.assert_called_once_with(db, RUN1_ID)
    tables = [call.args[0] for call in db.table.call_args_list]
    assert "document_processing_runs" in tables

# ============================================================================
# Canonical-text synchronization engine
# ============================================================================


def _ks(ks_id: str | None = None):
    return {
        "knowledge_source_id": ks_id or str(uuid4()),
        "institution_id": str(uuid4()),
        "source_type": "faq",
        "title": "Frequently Asked Questions",
    }


def test_sync_creates_new_document_for_first_time_record() -> None:
    db = MagicMock()
    ks = _ks()
    new_doc_id = str(uuid4())
    version_id = str(uuid4())
    run_id = str(uuid4())

    def table(name):
        m = MagicMock()
        if name == "knowledge_sources":
            m.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data=ks
            )
        elif name == "document_versions":
            m.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                MagicMock(data=[])
            )
        elif name == "documents":
            m.insert.return_value.execute.return_value = MagicMock(
                data=[{"document_id": new_doc_id}]
            )
        return m

    db.table.side_effect = table

    with (
        patch("app.services.admin_documents.get_r2_client", return_value=MagicMock()),
        patch("app.services.admin_documents.upload_file") as upload_mock,
        patch(
            "app.services.admin_documents.create_next_document_version",
            return_value={
                "document_version_id": version_id,
                "version_number": 1,
                "supersedes_version_id": None,
            },
        ) as next_version_mock,
        patch(
            "app.services.admin_documents.create_processing_run",
            return_value={"processing_run_id": run_id},
        ),
        patch(
            "app.services.admin_documents.process_run_to_retrieval",
            return_value={"chunks_created": 2, "status": "embedded"},
        ) as process_mock,
        patch(
            "app.services.admin_documents.update_document_version_lifecycle"
        ) as lifecycle_mock,
    ):
        result = svc.sync_canonical_text_record(
            institution_id=ks["institution_id"],
            source_type="faq",
            knowledge_source_title="FAQs",
            marker="faq:123",
            canonical_text="FAQ [general] Q\nA",
            actor_user_id="u1",
            client=db,
        )

    assert result["document_id"] == new_doc_id
    assert result["status"] == "synced"
    # version_label marker links the record to its synthetic document
    payload = next_version_mock.call_args.args[1]
    assert payload.version_label == "faq:123"
    assert payload.file_type == "txt"
    # canonical text uploaded to storage and pushed through the pipeline
    uploaded_text = upload_mock.call_args.args[3]
    assert uploaded_text == b"FAQ [general] Q\nA"
    process_mock.assert_called_once_with(run_id, db)
    lifecycle_mock.assert_called_once_with(db, version_id, "published")

def test_sync_update_supersedes_and_purges_stale_content() -> None:
    db = MagicMock()
    ks = _ks()
    existing_doc_id = str(uuid4())
    stale_version_id = str(uuid4())
    new_version_id = str(uuid4())
    run_id = str(uuid4())

    def table(name):
        m = MagicMock()
        if name == "knowledge_sources":
            m.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data=ks
            )
        elif name == "document_versions":
            m.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"document_id": existing_doc_id}]
            )
        return m

    db.table.side_effect = table

    with (
        patch(
            "app.services.admin_documents.get_document_with_versions",
            return_value=_run_doc([_version(stale_version_id, 1)]),
        ),
        patch(
            "app.services.admin_documents.purge_version_retrieval_content",
            return_value=[RUN1_ID],
        ) as purge_mock,
        patch(
            "app.services.admin_documents.get_r2_client", return_value=MagicMock()
        ),
        patch("app.services.admin_documents.upload_file"),
        patch(
            "app.services.admin_documents.create_next_document_version",
            return_value={
                "document_version_id": new_version_id,
                "version_number": 2,
                "supersedes_version_id": stale_version_id,
            },
        ),
        patch(
            "app.services.admin_documents.create_processing_run",
            return_value={"processing_run_id": run_id},
        ),
        patch(
            "app.services.admin_documents.process_run_to_retrieval",
            return_value={"chunks_created": 2, "status": "embedded"},
        ),
        patch("app.services.admin_documents.update_document_version_lifecycle"),
    ):
        result = svc.sync_canonical_text_record(
            institution_id=None,
            source_type="faq",
            knowledge_source_title="FAQs",
            marker="faq:123",
            canonical_text="updated text",
            actor_user_id="u1",
            client=db,
        )

    assert result["document_id"] == existing_doc_id
    # Stale retrieval content of the previous version is removed on update.
    purge_mock.assert_called_once_with(db, [stale_version_id])


def test_remove_canonical_text_record_deletes_document() -> None:
    db = MagicMock()
    existing_doc_id = str(uuid4())
    with (
        patch(
            "app.services.admin_documents.find_document_by_marker",
            return_value=existing_doc_id,
        ),
        patch(
            "app.services.admin_documents.delete_document",
            return_value={"deleted": True},
        ) as delete_mock,
    ):
        removed = svc.remove_canonical_text_record("faq:123", client=db)

    assert removed is True
    delete_mock.assert_called_once_with(existing_doc_id, client=db)


def test_remove_canonical_text_record_returns_false_when_absent() -> None:
    db = MagicMock()
    with patch(
        "app.services.admin_documents.find_document_by_marker", return_value=None
    ):
        removed = svc.remove_canonical_text_record("faq:none", client=db)
    assert removed is False





