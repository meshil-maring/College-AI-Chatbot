"""Document ingestion regressions: authorization."""

from __future__ import annotations

from .support import (
    KS_ID,
    _active_institution_authorization,
    _make_db_mock,
    _post_ingest,
    _post_ingest_as,
    client,
    io,
)


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
