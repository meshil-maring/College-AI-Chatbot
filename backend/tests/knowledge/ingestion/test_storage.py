"""Document ingestion regressions: storage."""

from __future__ import annotations

from .support import (
    DV_ID,
    FAKE_KS,
    INSTITUTION_ID,
    KS_ID,
    R2_BUCKET,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _make_db_mock,
    _make_r2_mock,
    _patch_auth,
    _post_ingest,
    client,
    hashlib,
    io,
    patch,
)


def test_ingest_checksum_stored_with_prefix():
    """Checksum passed to create_document_version must be 'sha256:<hex>'."""
    data = b"%PDF real content"
    expected = f"sha256:{hashlib.sha256(data).hexdigest()}"
    captured = {}

    def _spy(*args, **kwargs):
        captured["file_checksum"] = kwargs.get("file_checksum")
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
            files={"file": ("doc.pdf", io.BytesIO(data), "application/pdf")},
        )
    assert captured.get("file_checksum") == expected


# ---------------------------------------------------------------------------
# 8. Storage upload handling (R2)
# ---------------------------------------------------------------------------

def test_r2_put_object_is_called():
    r2 = _make_r2_mock()
    _post_ingest("doc.pdf", b"%PDF content", "application/pdf", r2_mock=r2)
    r2.put_object.assert_called_once()
    call_kwargs = r2.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] == R2_BUCKET
    assert call_kwargs["ContentType"] == "application/pdf"


def test_storage_object_key_contains_institution_and_ks_ids():
    response = _post_ingest("doc.pdf", b"%PDF content", "application/pdf")
    assert response.status_code == 201
    key = response.json()["storage_object_key"]
    assert INSTITUTION_ID in key
    assert KS_ID in key
