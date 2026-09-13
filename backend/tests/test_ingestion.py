"""
Tests for Phase 3.3 — Document Ingestion.

Unit tests mock all external I/O (Supabase DB + Cloudflare R2).
"""

import hashlib
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services.ingestion import _validate

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
USER_ID = "30000000-0000-0000-0000-000000000101"
KS_ID = "ks000000-0000-0000-0000-000000000001"
DOC_ID = "dc000000-0000-0000-0000-000000000001"
DV_ID = "dv000000-0000-0000-0000-000000000001"
RUN_ID = "pr000000-0000-0000-0000-000000000001"
R2_BUCKET = "college-ai-knowledge"

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}
FAKE_USER = {
    "id": USER_ID,
    "user_id": USER_ID,
    "auth_user_id": FAKE_CLAIMS["sub"],
    "email": FAKE_CLAIMS["email"],
    "roles": ["staff"],
}
FAKE_KS = {
    "knowledge_source_id": KS_ID,
    "institution_id": INSTITUTION_ID,
    "title": "Student Handbook",
    "source_type": "policy",
    "lifecycle_status": "draft",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers():
    return {"Authorization": "Bearer valid.token.here"}


def _patch_auth():
    p1 = patch("app.core.security.verify_jwt", return_value=FAKE_CLAIMS)
    p2 = patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=FAKE_USER))
    return p1, p2


def _make_db_mock(ks=FAKE_KS):
    """Mock for the Supabase admin DB client only (no storage)."""
    mock_db = MagicMock()

    def _table_side_effect(name):
        tbl = MagicMock()

        def _insert_side_effect(data):
            row_map = {
                "documents": {"document_id": DOC_ID, **data},
                "document_versions": {"document_version_id": DV_ID, **data},
                "document_processing_runs": {"processing_run_id": RUN_ID, **data},
            }
            result = MagicMock()
            result.execute.return_value.data = [row_map.get(name, data)]
            return result

        tbl.insert.side_effect = _insert_side_effect

        select_chain = MagicMock()
        select_chain.eq.return_value.maybe_single.return_value.execute.return_value.data = ks
        tbl.select.return_value = select_chain

        return tbl

    mock_db.table.side_effect = _table_side_effect
    return mock_db


def _make_r2_mock():
    """Mock for the boto3 S3/R2 client."""
    r2 = MagicMock()
    r2.put_object.return_value = {}
    r2.delete_object.return_value = {}
    return r2


def _post_ingest(
    filename: str,
    content: bytes,
    content_type: str,
    ks_id: str = KS_ID,
    db_mock=None,
    r2_mock=None,
):
    p1, p2 = _patch_auth()
    db = db_mock if db_mock is not None else _make_db_mock()
    r2 = r2_mock if r2_mock is not None else _make_r2_mock()
    with (
        p1,
        p2,
        patch("app.services.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=r2),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": ks_id},
            files={"file": (filename, io.BytesIO(content), content_type)},
        )


# ---------------------------------------------------------------------------
# 1–3. Valid file type ingestion
# ---------------------------------------------------------------------------

def test_ingest_pdf_success():
    response = _post_ingest("syllabus.pdf", b"%PDF-1.4 fake content", "application/pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert body["knowledge_source_id"] == KS_ID
    assert body["document_id"] == DOC_ID
    assert body["document_version_id"] == DV_ID
    assert body["processing_run_id"] == RUN_ID
    assert "syllabus.pdf" in body["storage_object_key"]


def test_ingest_docx_success():
    response = _post_ingest(
        "handbook.docx",
        b"PK fake docx bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_ingest_txt_success():
    response = _post_ingest("notes.txt", b"plain text content", "text/plain")
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


# ---------------------------------------------------------------------------
# 4. Unsupported file type rejection
# ---------------------------------------------------------------------------

def test_ingest_rejects_unsupported_extension():
    response = _post_ingest("malware.exe", b"MZ", "application/pdf")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_ingest_rejects_bad_mime():
    response = _post_ingest("report.pdf", b"%PDF", "application/octet-stream")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_MIME_TYPE"


# ---------------------------------------------------------------------------
# 5. Empty file rejection
# ---------------------------------------------------------------------------

def test_ingest_rejects_empty_file():
    response = _post_ingest("empty.pdf", b"", "application/pdf")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_FILE"


# ---------------------------------------------------------------------------
# 6. Oversized file rejection
# ---------------------------------------------------------------------------

def test_ingest_rejects_oversized_file():
    big = b"x" * (51 * 1024 * 1024)
    response = _post_ingest("big.pdf", big, "application/pdf")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------------------
# 7. SHA-256 checksum generation
# ---------------------------------------------------------------------------

def test_sha256_checksum_is_deterministic():
    data = b"hello world"
    h1 = hashlib.sha256(data).hexdigest()
    h2 = hashlib.sha256(data).hexdigest()
    assert len(h1) == 64
    assert h1 == h2


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
        patch("app.services.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.ingestion.create_document_version", side_effect=_spy),
        patch(
            "app.services.ingestion.create_processing_run",
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


# ---------------------------------------------------------------------------
# 9. Knowledge source validation
# ---------------------------------------------------------------------------

def test_ingest_rejects_unknown_knowledge_source():
    response = _post_ingest("doc.pdf", b"%PDF", "application/pdf", db_mock=_make_db_mock(ks=None))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"


def test_ingest_requires_auth():
    response = client.post(
        "/api/v1/documents/ingest",
        data={"knowledge_source_id": KS_ID},
        files={"file": ("f.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 9b. Role-based authorization
# ---------------------------------------------------------------------------

def _post_ingest_as(role: str | None):
    """POST /ingest with a user whose only role is `role` (or no roles if None)."""
    claims = {**FAKE_CLAIMS}
    user = {**FAKE_USER, "roles": [role] if role else []}
    p1 = patch("app.core.security.verify_jwt", return_value=claims)
    p2 = patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user))
    db = _make_db_mock()
    r2 = _make_r2_mock()
    with (
        p1,
        p2,
        patch("app.services.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=r2),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")},
        )


def test_ingest_student_is_forbidden():
    response = _post_ingest_as("student")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_ingest_faculty_is_allowed():
    response = _post_ingest_as("faculty")
    assert response.status_code == 201


def test_ingest_staff_is_allowed():
    response = _post_ingest_as("staff")
    assert response.status_code == 201


def test_ingest_admin_is_allowed():
    response = _post_ingest_as("admin")
    assert response.status_code == 201


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
        patch("app.services.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.ingestion.create_document_version", side_effect=_spy),
        patch(
            "app.services.ingestion.create_processing_run",
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
        patch("app.services.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.ingestion.create_processing_run", side_effect=_spy),
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
        patch("app.services.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_admin_client", return_value=_make_db_mock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=_make_r2_mock()),
        patch("app.services.ingestion.create_processing_run", side_effect=_spy),
    ):
        client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )

    assert captured.get("processor_name") is not None
    assert captured.get("processor_version") is not None


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
        patch("app.services.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=r2),
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
        patch("app.services.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_admin_client", return_value=db),
        patch("app.api.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.ingestion.get_r2_client", return_value=r2),
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


def test_validation_failure_creates_no_db_records():
    db = _make_db_mock()
    r2 = _make_r2_mock()
    _post_ingest("bad.exe", b"MZ", "application/pdf", db_mock=db, r2_mock=r2)
    db.table.assert_not_called()
    r2.put_object.assert_not_called()


# ---------------------------------------------------------------------------
# _validate unit tests (no HTTP)
# ---------------------------------------------------------------------------

def test_validate_rejects_empty():
    with pytest.raises(AppError) as exc:
        _validate("doc.pdf", "application/pdf", 0)
    assert exc.value.code == "EMPTY_FILE"


def test_validate_rejects_unsupported_extension():
    with pytest.raises(AppError) as exc:
        _validate("report.exe", "application/pdf", 100)
    assert exc.value.code == "INVALID_FILE_TYPE"


def test_validate_rejects_bad_mime():
    with pytest.raises(AppError) as exc:
        _validate("report.pdf", "application/octet-stream", 100)
    assert exc.value.code == "INVALID_MIME_TYPE"


def test_validate_rejects_oversized():
    with pytest.raises(AppError) as exc:
        _validate("report.pdf", "application/pdf", 51 * 1024 * 1024)
    assert exc.value.code == "FILE_TOO_LARGE"


def test_validate_accepts_pdf():
    _validate("report.pdf", "application/pdf", 1024)


def test_validate_accepts_docx():
    _validate(
        "doc.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        2048,
    )


def test_validate_accepts_txt():
    _validate("notes.txt", "text/plain", 512)
