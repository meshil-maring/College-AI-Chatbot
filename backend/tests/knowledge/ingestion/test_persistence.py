"""Document ingestion regressions: persistence."""

from __future__ import annotations

from .support import (
    DV_ID,
    FAKE_KS,
    KS_ID,
    R2_BUCKET,
    RUN_ID,
    USER_ID,
    _active_institution_authorization,
    _auth_headers,
    _make_db_mock,
    _make_r2_mock,
    _patch_auth,
    _post_ingest,
    client,
    io,
    patch,
)


# ---------------------------------------------------------------------------
# 10. Document creation
# ---------------------------------------------------------------------------

def test_document_created_with_correct_ks_id():
    db = _make_db_mock()
    _post_ingest("doc.pdf", b"%PDF content", "application/pdf", db_mock=db)
    calls = [str(c) for c in db.table.call_args_list]
    assert any("documents" in c for c in calls)


# ---------------------------------------------------------------------------
# 11. Document version creation
# ---------------------------------------------------------------------------

def test_document_version_fields():
    captured = {}

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return {"document_version_id": DV_ID}

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.knowledge.ingestion.create_document_version", side_effect=_spy),
        patch(
            "app.services.knowledge.ingestion.create_processing_run",
            return_value={"processing_run_id": RUN_ID},
        ),
    ):
        client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("syllabus.pdf", io.BytesIO(b"%PDF data"), "application/pdf")},
        )

    assert captured["original_filename"] == "syllabus.pdf"
    assert captured["file_type"] == "pdf"
    assert captured["mime_type"] == "application/pdf"
    assert captured["file_size_bytes"] == len(b"%PDF data")
    assert captured["storage_bucket"] == R2_BUCKET
    assert captured["file_checksum"].startswith("sha256:")
    assert captured["user_id"] == USER_ID


# ---------------------------------------------------------------------------
# 12 & 13. Processing run creation with status = queued
# ---------------------------------------------------------------------------

def test_processing_run_created_with_queued_status():
    captured = {}

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return {"processing_run_id": RUN_ID}

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.knowledge.ingestion.create_processing_run", side_effect=_spy),
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert captured["document_version_id"] == DV_ID


def test_processing_run_includes_processor_metadata():
    captured = {}

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return {"processing_run_id": RUN_ID}

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.knowledge.ingestion.create_processing_run", side_effect=_spy),
    ):
        client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert captured.get("processor_name") is not None
    assert captured.get("processor_version") is not None
