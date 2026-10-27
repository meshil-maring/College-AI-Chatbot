"""Document ingestion regressions: failures."""

from __future__ import annotations

from .support import (
    FAKE_KS,
    KS_ID,
    R2_BUCKET,
    _active_institution_authorization,
    _auth_headers,
    _make_db_mock,
    _make_r2_mock,
    _patch_auth,
    client,
    io,
    patch,
)


# ---------------------------------------------------------------------------
# 14. Failure handling
# ---------------------------------------------------------------------------

def test_r2_upload_failure_returns_500_no_db_records():
    r2 = _make_r2_mock()
    r2.put_object.side_effect = Exception("R2 unavailable")
    db = _make_db_mock()

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=r2),
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert response.status_code == 500
    insert_tables = [c.args[0] for c in db.table.call_args_list if c.args]
    assert "document_versions" not in insert_tables
    assert "document_processing_runs" not in insert_tables


def test_db_failure_after_r2_upload_triggers_r2_cleanup():
    r2 = _make_r2_mock()
    db = _make_db_mock()

    original_side_effect = db.table.side_effect

    def _failing_table(name):
        tbl = original_side_effect(name)
        if name == "document_versions":
            tbl.insert.side_effect = Exception("DB write failed")
        return tbl

    db.table.side_effect = _failing_table

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=r2),
    ):
        response = client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "REGISTRATION_FAILED"
    r2.delete_object.assert_called_once()
    call_kwargs = r2.delete_object.call_args.kwargs
    assert call_kwargs["Bucket"] == R2_BUCKET
