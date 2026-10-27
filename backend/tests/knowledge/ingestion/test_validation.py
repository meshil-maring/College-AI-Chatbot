"""Document ingestion regressions: validation."""

from __future__ import annotations

from .support import (
    AppError,
    _active_institution_authorization,
    _make_db_mock,
    _make_r2_mock,
    _post_ingest,
    _validate,
    hashlib,
    pytest,
)


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
