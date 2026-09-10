"""Phase Admin-3 tests — Admin API endpoints.

Covers: admin authorization (401/403), identity/status, dashboard, knowledge
sources, documents orchestration, FAQ/notice CRUD + RAG sync triggers, student
management, results management, CSV upload, test results, attendance, and
audit logging on every mutation.
"""

import itertools
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ADMIN_USER = {
    "user_id": "70000000-0000-0000-0000-000000000001",
    "auth_user_id": "70000000-0000-0000-0000-0000000000aa",
    "email": "admin@example.com",
    "roles": ["admin"],
}
STUDENT_USER = {
    "user_id": "70000000-0000-0000-0000-000000000002",
    "auth_user_id": "70000000-0000-0000-0000-0000000000bb",
    "email": "student@example.com",
    "roles": ["student"],
}
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
KS_ID = str(uuid4())
FAQ_ID = str(uuid4())
NOTICE_ID = str(uuid4())
STUDENT_ID = str(uuid4())
RESULT_ID = str(uuid4())
TEST_RESULT_ID = str(uuid4())
ATTENDANCE_ID = str(uuid4())
DOC_ID = str(uuid4())


@pytest.fixture(autouse=True)
def admin_auth():
    """All tests in this module run as an authenticated admin by default."""
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _audit_db(first_insert: dict | None = None):
    """Mock service-role client for the API layer (audit + simple inserts).

    The first ``.insert()`` returns ``first_insert`` (the created entity row);
    every later insert (typically the audit-log row) returns a generic row.
    """
    db = MagicMock()
    first = MagicMock(data=[first_insert if first_insert is not None else {"id": "x"}])
    audit = MagicMock(data=[{"audit_id": str(uuid4())}])
    db.table.return_value.insert.return_value.execute.side_effect = itertools.chain(
        [first], itertools.repeat(audit)
    )
    return db


def _audit_rows(db):
    """Extract rows passed to .insert() calls on the shared mock chain."""
    return [
        call.args[0]
        for call in db.table.return_value.insert.call_args_list
        if call.args
    ]


# ============================================================================
# Authorization
# ============================================================================


def test_admin_endpoint_requires_authentication() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_endpoint_forbidden_for_non_admin_role() -> None:
    app.dependency_overrides[get_current_user] = lambda: STUDENT_USER
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_me_returns_identity_and_status() -> None:
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == ADMIN_USER["user_id"]
    assert body["email"] == ADMIN_USER["email"]
    assert body["roles"] == ["admin"]
    assert body["is_admin"] is True


# ============================================================================
# Dashboard
# ============================================================================


def test_dashboard_returns_counts_and_recent_audit() -> None:
    summary = {
        "counts": {"faqs": 3, "notices": 2, "students": 25},
        "recent_audit": [{"audit_id": str(uuid4()), "action": "faq.create"}],
    }
    with patch(
        "app.services.admin_dashboard.get_dashboard_summary", return_value=summary
    ):
        response = client.get(
            f"/api/v1/admin/dashboard?institution_id={INSTITUTION_ID}"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["faqs"] == 3
    assert body["counts"]["students"] == 25
    assert body["recent_audit"][0]["action"] == "faq.create"

# ============================================================================
# Knowledge sources
# ============================================================================


def test_create_knowledge_source_audits_mutation() -> None:
    db = _audit_db(first_insert={"knowledge_source_id": KS_ID})
    with patch("app.api.admin.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/knowledge-sources",
            json={
                "institution_id": INSTITUTION_ID,
                "source_type": "handbook",
                "title": "Student Handbook",
            },
        )

    assert response.status_code == 201
    assert response.json()["knowledge_source_id"] == KS_ID
    tables = [call.args[0] for call in db.table.call_args_list]
    assert "knowledge_sources" in tables
    assert "admin_audit_log" in tables
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "knowledge_source.create"
    assert audit_rows[0]["actor_user_id"] == ADMIN_USER["user_id"]


def test_update_knowledge_source_404_when_missing() -> None:
    db = _audit_db()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    with patch("app.api.admin.get_admin_client", return_value=db):
        response = client.patch(
            f"/api/v1/admin/knowledge-sources/{KS_ID}", json={"title": "New"}
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"


# ============================================================================
# Documents (upload orchestration + versioning + delete)
# ============================================================================


def test_document_upload_endpoint_orchestrates_and_audits() -> None:
    upload_result = {
        "document_id": DOC_ID,
        "document_version_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "status": "embedded",
    }
    db = _audit_db()
    with (
        patch(
            "app.services.admin_documents.upload_document",
            new=AsyncMock(return_value=upload_result),
        ),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("handbook.pdf", b"pdf-bytes", "application/pdf")},
            data={"knowledge_source_id": KS_ID, "auto_process": "true"},
        )

    assert response.status_code == 201
    assert response.json()["document_id"] == DOC_ID
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.upload"


def test_document_version_endpoint_uses_versioning_and_audits() -> None:
    version_result = {
        "document_id": DOC_ID,
        "document_version_id": str(uuid4()),
        "version_number": 2,
        "supersedes_version_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "status": "queued",
    }
    db = _audit_db()
    with (
        patch(
            "app.services.admin_documents.update_document",
            new=AsyncMock(return_value=version_result),
        ),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            f"/api/v1/admin/documents/{DOC_ID}/versions",
            files={"file": ("handbook-v2.pdf", b"pdf-bytes-2", "application/pdf")},
            data={"auto_process": "false"},
        )

    assert response.status_code == 201
    assert response.json()["version_number"] == 2
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.update"
    assert audit_rows[0]["record_id"] == DOC_ID


def test_document_delete_endpoint_audits() -> None:
    db = _audit_db()
    with (
        patch(
            "app.services.admin_documents.delete_document",
            return_value={"deleted": True, "document_id": DOC_ID},
        ),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.delete(f"/api/v1/admin/documents/{DOC_ID}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.delete"

# ============================================================================
# FAQs and notices (RAG sync triggers + audit)
# ============================================================================


def _faq_row() -> dict:
    return {
        "faq_id": FAQ_ID,
        "institution_id": INSTITUTION_ID,
        "category": "general",
        "question": "When is the library open?",
        "answer": "8am to 10pm on weekdays.",
        "display_order": 0,
        "is_active": True,
    }


def test_create_faq_endpoint_triggers_rag_sync_and_audit() -> None:
    faq = _faq_row()
    db = _audit_db(first_insert=faq)
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch(
            "app.services.admin_faq.sync_canonical_text_record"
        ) as sync_mock,
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/faqs",
            json={
                "institution_id": INSTITUTION_ID,
                "question": faq["question"],
                "answer": faq["answer"],
            },
        )

    assert response.status_code == 201
    sync_mock.assert_called_once()
    kwargs = sync_mock.call_args.kwargs
    assert kwargs["marker"] == f"faq:{FAQ_ID}"
    assert kwargs["institution_id"] == INSTITUTION_ID
    assert kwargs["source_type"] == "faq"
    assert faq["question"] in kwargs["canonical_text"]
    assert faq["answer"] in kwargs["canonical_text"]
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.create"


def test_update_faq_deactivation_removes_retrievable_content() -> None:
    db = _audit_db()
    updated = _faq_row() | {"is_active": False}
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[updated])
    )
    get_faq_mock = MagicMock(return_value=_faq_row())
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", get_faq_mock),
        patch("app.services.admin_faq.sync_canonical_text_record") as sync_mock,
        patch(
            "app.services.admin_faq.remove_canonical_text_record"
        ) as remove_mock,
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.patch(
            f"/api/v1/admin/faqs/{FAQ_ID}", json={"is_active": False}
        )

    assert response.status_code == 200
    sync_mock.assert_not_called()
    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.update"


def test_delete_faq_endpoint_removes_rag_content_and_audits() -> None:
    db = _audit_db()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_knowledge.get_faq",
            return_value=_faq_row(),
        ),
        patch(
            "app.services.admin_faq.remove_canonical_text_record"
        ) as remove_mock,
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.delete(f"/api/v1/admin/faqs/{FAQ_ID}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.delete"


def test_create_notice_endpoint_triggers_rag_sync_and_audit() -> None:
    notice = {
        "notice_id": NOTICE_ID,
        "institution_id": INSTITUTION_ID,
        "title": "Exam schedule",
        "content": "Midterms start Monday.",
        "category": "exam",
        "priority": "high",
        "is_active": True,
    }
    db = _audit_db(first_insert=notice)
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch(
            "app.services.admin_notices.sync_canonical_text_record"
        ) as sync_mock,
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/notices",
            json={
                "institution_id": INSTITUTION_ID,
                "title": notice["title"],
                "content": notice["content"],
                "category": "exam",
                "priority": "high",
            },
        )

    assert response.status_code == 201
    sync_mock.assert_called_once()
    kwargs = sync_mock.call_args.kwargs
    assert kwargs["marker"] == f"notice:{NOTICE_ID}"
    assert kwargs["source_type"] == "notice"
    assert notice["title"] in kwargs["canonical_text"]
    assert notice["content"] in kwargs["canonical_text"]
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "notice.create"

# ============================================================================
# Students management
# ============================================================================


def _student_row() -> dict:
    return {
        "student_id": STUDENT_ID,
        "user_id": str(uuid4()),
        "institution_id": INSTITUTION_ID,
        "student_number": "S001",
        "status": "active",
        "is_active": True,
    }


def test_create_student_endpoint_audits() -> None:
    db = _audit_db(first_insert=_student_row())
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/students",
            json={
                "user_id": str(uuid4()),
                "institution_id": INSTITUTION_ID,
                "student_number": "S001",
                "enrollment_date": "2026-08-01",
            },
        )

    assert response.status_code == 201
    assert response.json()["student_id"] == STUDENT_ID
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "student.create"


def test_create_student_rejects_invalid_status() -> None:
    db = _audit_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/students",
            json={
                "user_id": str(uuid4()),
                "institution_id": INSTITUTION_ID,
                "student_number": "S002",
                "enrollment_date": "2026-08-01",
                "status": "bogus",
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_STUDENT_STATUS"


def test_archive_student_endpoint_soft_deletes_and_audits() -> None:
    db = _audit_db()
    archived = _student_row() | {"status": "inactive", "is_active": False}
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[archived])
    )
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.repositories.admin_academics.get_student", return_value=_student_row()),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.delete(f"/api/v1/admin/students/{STUDENT_ID}")

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    update_fields = db.table.return_value.update.call_args.args[0]
    assert update_fields == {"status": "inactive", "is_active": False}
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "student.archive"


def test_create_result_with_items_audits() -> None:
    db = _audit_db(first_insert={"student_result_id": RESULT_ID})
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/results",
            json={
                "student_id": STUDENT_ID,
                "academic_year_id": str(uuid4()),
                "semester_id": str(uuid4()),
                "program_id": str(uuid4()),
                "result_type": "semester",
                "sgpa": 8.5,
                "items": [
                    {
                        "course_id": str(uuid4()),
                        "credits_earned": 4,
                        "letter_grade": "A",
                    }
                ],
            },
        )

    assert response.status_code == 201
    tables = [call.args[0] for call in db.table.call_args_list]
    assert "student_results" in tables
    assert "student_result_items" in tables
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "result.create"


def test_create_result_rejects_invalid_result_type() -> None:
    db = _audit_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/results",
            json={
                "student_id": STUDENT_ID,
                "academic_year_id": str(uuid4()),
                "semester_id": str(uuid4()),
                "program_id": str(uuid4()),
                "result_type": "bogus",
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_RESULT_TYPE"

# ============================================================================
# Results CSV upload
# ============================================================================


CSV_HEADER = (
    "student_number,academic_year_id,semester_id,program_id,result_type,"
    "total_credits_earned,total_credits_max,sgpa,cgpa,status,issued_at\n"
)
AY_ID = str(uuid4())
SEM_ID = str(uuid4())
PROG_ID = str(uuid4())


def _csv_db() -> MagicMock:
    db = _audit_db()
    students_chain = (
        db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.range.return_value
    )
    students_chain.execute.return_value = MagicMock(data=[_student_row()])
    db.table.return_value.insert.return_value.execute.side_effect = itertools.repeat(
        MagicMock(data=[{"student_result_id": RESULT_ID}])
    )
    return db


def test_csv_upload_inserts_valid_rows_and_reports_row_errors() -> None:
    csv_text = (
        CSV_HEADER
        # valid row
        + f"S001,{AY_ID},{SEM_ID},{PROG_ID},semester,24,26,8.5,8.0,published,\n"
        # invalid UUID
        + f"S001,not-a-uuid,{SEM_ID},{PROG_ID},semester,,,,,,\n"
        # unknown student number
        + f"S999,{AY_ID},{SEM_ID},{PROG_ID},semester,,,,,,\n"
    )
    db = _csv_db()
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/results/csv-upload",
            files={"file": ("results.csv", csv_text.encode("utf-8"), "text/csv")},
            data={"institution_id": INSTITUTION_ID},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    assert body["inserted_count"] == 1
    assert body["failed_count"] == 0
    assert len(body["row_errors"]) == 2
    error_rows = {e["row"]: e for e in body["row_errors"]}
    assert any("valid UUID" in msg for msg in error_rows[3]["errors"])
    assert any("not found" in msg for msg in error_rows[4]["errors"])
    inserted = db.table.return_value.insert.call_args_list[0].args[0]
    assert inserted["student_id"] == STUDENT_ID
    assert inserted["sgpa"] == 8.5
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "result.csv_upload"
    assert audit_rows[0]["record_data"]["inserted_count"] == 1


def test_csv_upload_rejects_missing_columns() -> None:
    db = _csv_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/results/csv-upload",
            files={"file": ("bad.csv", b"student_number,sgpa\nS001,8.5\n", "text/csv")},
            data={"institution_id": INSTITUTION_ID},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CSV_MISSING_COLUMNS"

# ============================================================================
# Test results + attendance management
# ============================================================================


def test_create_test_result_audits() -> None:
    db = _audit_db(first_insert={"test_result_id": TEST_RESULT_ID})
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/test-results",
            json={
                "student_id": STUDENT_ID,
                "course_id": str(uuid4()),
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "test_name": "Quiz 1",
                "test_type": "quiz",
                "max_marks": 20,
                "scored_marks": 18,
            },
        )

    assert response.status_code == 201
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "test_result.create"


def test_create_test_result_rejects_scored_over_max() -> None:
    db = _audit_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/test-results",
            json={
                "student_id": STUDENT_ID,
                "course_id": str(uuid4()),
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "test_name": "Quiz 1",
                "test_type": "quiz",
                "max_marks": 20,
                "scored_marks": 25,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SCORES"


def test_create_test_result_rejects_invalid_test_type() -> None:
    db = _audit_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/test-results",
            json={
                "student_id": STUDENT_ID,
                "course_id": str(uuid4()),
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "test_name": "Quiz 1",
                "test_type": "bogus",
                "max_marks": 20,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TEST_TYPE"


def test_create_attendance_audits_and_rejects_bad_status() -> None:
    payload = {
        "student_id": STUDENT_ID,
        "section_id": str(uuid4()),
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "date": "2026-09-01",
        "status": "present",
    }

    db = _audit_db(first_insert={"student_attendance_id": ATTENDANCE_ID})
    with (
        patch("app.services.admin_academics.get_admin_client", return_value=db),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        response = client.post("/api/v1/admin/attendance", json=payload)
    assert response.status_code == 201
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "attendance.create"

    db2 = _audit_db()
    with patch("app.services.admin_academics.get_admin_client", return_value=db2):
        response = client.post(
            "/api/v1/admin/attendance", json=payload | {"status": "bogus"}
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ATTENDANCE_STATUS"


def test_create_attendance_reports_duplicate_as_conflict() -> None:
    db = _audit_db()
    db.table.return_value.insert.return_value.execute.side_effect = Exception(
        "duplicate key value violates unique constraint"
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/attendance",
            json={
                "student_id": STUDENT_ID,
                "section_id": str(uuid4()),
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "date": "2026-09-01",
                "status": "present",
            },
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ATTENDANCE_CREATE_FAILED"


# ============================================================================
# Audit-log endpoints
# ============================================================================


def test_list_audit_logs_endpoint() -> None:
    entry = {"audit_id": str(uuid4()), "action": "faq.create", "table_name": "faqs"}
    db = _audit_db()
    (
        db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value
    ).execute.return_value = MagicMock(data=[entry])
    with patch("app.api.admin.get_admin_client", return_value=db):
        response = client.get("/api/v1/admin/audit-logs?action=faq.create")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "faq.create"


def test_get_audit_log_404_when_missing() -> None:
    db = _audit_db()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        MagicMock(data=None)
    )
    with patch("app.api.admin.get_admin_client", return_value=db):
        response = client.get(f"/api/v1/admin/audit-logs/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIT_NOT_FOUND"





