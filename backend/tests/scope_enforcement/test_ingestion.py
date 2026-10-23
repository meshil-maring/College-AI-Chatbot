"""Test ingestion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    DV_ID,
    KS_A,
    KS_B,
    RUN_ID,
    TENANT_A,
    TENANT_B,
    _as,
    _clear,
    _user,
    client,
)


def test_06_faculty_isolation_on_ingestion_pipeline():
    """A faculty of Institution A cannot ingest/extract for Institution B."""
    faculty = _user(TENANT_A, roles=("faculty",))
    _as(faculty)
    try:
        # /documents/ingest against a foreign knowledge source -> 403.
        with (
            patch(
                "app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()
            ),
            patch(
                "app.api.knowledge.ingestion.get_knowledge_source",
                return_value={
                    "knowledge_source_id": KS_B,
                    "institution_id": TENANT_B,
                },
            ),
            patch("app.api.knowledge.ingestion.ingest_document") as ingest,
        ):
            resp = client.post(
                "/api/v1/documents/ingest",
                files={"file": ("doc.txt", b"hello", "text/plain")},
                data={"knowledge_source_id": KS_B},
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        ingest.assert_not_called()

        # NEW Phase 6.13.7 guard: extract for a run whose knowledge source
        # belongs to Institution B is rejected even though the run id is valid.
        run = {
            "processing_run_id": RUN_ID,
            "status": "queued",
            "document_version_id": DV_ID,
            "document_versions": {
                "document_version_id": DV_ID,
                "storage_bucket": "bucket",
                "storage_object_key": "key",
                "file_type": "txt",
                "knowledge_source_id": KS_B,
            },
        }
        with (
            patch(
                "app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()
            ),
            patch(
                "app.api.knowledge.ingestion.get_processing_run_with_version",
                return_value=run,
            ),
            patch(
                "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_B},
            ),
            patch("app.api.knowledge.ingestion.update_run_status") as update_status,
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        update_status.assert_not_called()

        # Same-tenant run flows through (guard passes).
        run_same = {
            **run,
            "document_versions": {
                **run["document_versions"],
                "knowledge_source_id": KS_A,
            },
        }
        with (
            patch(
                "app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()
            ),
            patch(
                "app.api.knowledge.ingestion.get_processing_run_with_version",
                return_value=run_same,
            ),
            patch(
                "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_A},
            ),
            patch("app.api.knowledge.ingestion.update_run_status"),
            patch("app.api.knowledge.ingestion.store_extracted_text"),
            patch(
                "app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()
            ),
            patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
            patch("app.api.knowledge.ingestion.extract_text", return_value="text"),
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        assert resp.status_code == 200, resp.text
    finally:
        _clear()


def test_06b_embed_guard_denies_foreign_tenant_run():
    """The embed route resolves the run server-side; foreign tenant -> 403."""
    faculty = _user(TENANT_A, roles=("faculty",))
    run = {
        "processing_run_id": RUN_ID,
        "status": "ready",
        "document_versions": {
            "document_version_id": DV_ID,
            "knowledge_source_id": KS_B,
        },
    }
    _as(faculty)
    try:
        with (
            patch(
                "app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()
            ),
            patch(
                "app.api.knowledge.ingestion.get_processing_run_with_version",
                return_value=run,
            ),
            patch(
                "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
                return_value={"institution_id": TENANT_B},
            ),
            patch("app.api.knowledge.ingestion.embed_processing_run") as embed,
        ):
            resp = client.post(f"/api/v1/documents/{RUN_ID}/embed")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    embed.assert_not_called()
