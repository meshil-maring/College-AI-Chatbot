"""Phase 6.6 — RBAC verification tests (LOCKED Phase 6.1-6.5 baseline).

Verification only: no production-code changes. Proves authentication (401),
role (403), tenant (403 TENANT_MISMATCH), tampering-inertness, ownership,
and fail-closed behavior across admin / approval / ingestion / student-me /
conversations / chat operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.admin import _ADMIN, _APPROVAL
from app.api.ingestion import _INGEST_ALLOWED
from app.core.security import get_current_user
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_A = "30000000-0000-0000-0000-000000000151"
KS_ID = "40000000-0000-0000-0000-000000000111"
RUN_ID = "a0000000-0000-0000-0000-000000000001"


def _user(tenant=None, roles=("admin",)):
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "rbac@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    for dep in (get_current_user, _ADMIN, _APPROVAL, _INGEST_ALLOWED):
        app.dependency_overrides.pop(dep, None)


def test_unauthenticated_admin_me_is_401():
    _clear()
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 401


def test_unauthenticated_approval_endpoints_are_401():
    _clear()
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (401, 401, 401)


def test_unauthenticated_ingest_endpoints_are_401():
    _clear()
    try:
        r0 = client.post("/api/v1/documents/ingest")
        r1 = client.post(f"/api/v1/documents/{RUN_ID}/extract")
        r2 = client.post(f"/api/v1/documents/{RUN_ID}/chunk")
        r3 = client.post(f"/api/v1/documents/{RUN_ID}/embed")
    finally:
        _clear()
    assert (r0.status_code, r1.status_code, r2.status_code, r3.status_code) == (
        401, 401, 401, 401)


def test_unauthenticated_student_me_endpoints_are_401():
    _clear()
    try:
        paths = [
            "/api/v1/students/me/profile",
            "/api/v1/students/me/results",
            "/api/v1/students/me/test-results",
            "/api/v1/students/me/attendance",
        ]
        statuses = [client.get(path).status_code for path in paths]
    finally:
        _clear()
    assert statuses == [401, 401, 401, 401]


def test_unauthenticated_conversations_and_chat_are_401():
    _clear()
    try:
        r1 = client.get("/api/v1/conversations")
        r2 = client.get(f"/api/v1/conversations/{uuid4()}/messages")
        r3 = client.post(
            "/api/v1/generation/chat",
            json={"user_query": "hello", "institution_id": TENANT_A},
        )
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (401, 401, 401)

def test_admin_can_access_permitted_admin_operation():
    _as(_user(None, roles=("admin",)))
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True


def test_institution_admin_cannot_cross_tenant_on_admin_list():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students"
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    list_students.assert_not_called()


def test_institution_admin_forced_to_own_institution():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students", return_value=[]
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students?institution_id={TENANT_A}"
            )
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(list_students.call_args.args[0]) == TENANT_A


def test_platform_admin_retains_global_authority():
    _as(_user(None, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students", return_value=[]
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(list_students.call_args.args[0]) == TENANT_B


def test_staff_can_approve_own_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))
    row = {"student_id": STUDENT_A, "approval_status": "approved"}
    try:
        with (
            patch(
                "app.api.admin.admin_academics.approve_student",
                return_value=row,
            ) as approve,
            patch("app.api.admin._record_audit"),
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 200
    approve.assert_called_once()


def test_staff_cannot_access_admin_only_operations():
    _as(_user(TENANT_A, roles=("staff",)))
    try:
        r1 = client.get("/api/v1/admin/me")
        r2 = client.get("/api/v1/admin/audit-logs")
        r3 = client.get(f"/api/v1/admin/students/{STUDENT_A}")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert r3.status_code == 403


def test_platform_staff_cannot_obtain_platform_admin_authority():
    _as(_user(None, roles=("staff",)))
    try:
        with patch(
            "app.api.admin.admin_academics.approve_student"
        ) as approve:
            r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
            r2 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert r1.json()["error"]["code"] == "FORBIDDEN"
    assert r2.json()["error"]["code"] == "FORBIDDEN"
    approve.assert_not_called()

def test_faculty_can_reach_permitted_ingestion_operation():
    faculty = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "faculty@college.edu",
        "roles": ["faculty"],
    }
    run = {
        "processing_run_id": RUN_ID,
        "status": "ready",
        "document_versions": {"document_version_id": str(uuid4())},
    }
    claims = {"sub": faculty["auth_user_id"], "email": faculty["email"]}
    p1 = patch("app.core.security.verify_jwt", return_value=claims)
    p2 = patch(
        "app.db.supabase.get_user_by_auth_id",
        new=AsyncMock(return_value=faculty),
    )
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.ingestion.get_processing_run_with_version",
            return_value=run,
        ),
        patch("app.api.ingestion.get_extracted_text", return_value="text"),
        patch("app.api.ingestion.delete_chunks_for_run"),
        patch("app.api.ingestion.insert_chunks"),
        patch("app.api.ingestion.update_run_status"),
    ):
        resp = client.post(
            f"/api/v1/documents/{RUN_ID}/chunk",
            headers={"Authorization": "Bearer faculty.token"},
        )
    assert resp.status_code == 200


def test_faculty_cannot_access_admin_only_operation():
    _as(_user(TENANT_A, roles=("faculty",)))
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_faculty_cannot_access_staff_only_approval_operation():
    _as(_user(TENANT_A, roles=("faculty",)))
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (403, 403, 403)


def test_faculty_cannot_cross_tenant_on_ingest():
    faculty = {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "faculty@college.edu",
        "roles": ["faculty"],
        "institution_id": TENANT_A,
    }
    ks = {"knowledge_source_id": KS_ID, "institution_id": TENANT_B}
    claims = {"sub": faculty["auth_user_id"], "email": faculty["email"]}
    p1 = patch("app.core.security.verify_jwt", return_value=claims)
    p2 = patch(
        "app.db.supabase.get_user_by_auth_id",
        new=AsyncMock(return_value=faculty),
    )
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_knowledge_source", return_value=ks),
    ):
        resp = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": "Bearer faculty.token"},
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", b"%PDF", "application/pdf")},
        )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_student_can_access_own_profile():
    student_user_id = "71000000-0000-0000-0000-000000000001"
    row = {
        "student_id": str(uuid4()),
        "user_id": student_user_id,
        "institution_id": TENANT_A,
        "student_number": "S100",
        "status": "active",
        "is_active": True,
    }
    _as(
        {
            "user_id": student_user_id,
            "auth_user_id": str(uuid4()),
            "email": "student@example.com",
            "roles": ["student"],
            "institution_id": TENANT_A,
        }
    )
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.maybe_single.return_value.execute.return_value = MagicMock(data=row)
    try:
        with patch(
            "app.services.student_data.get_admin_client", return_value=db
        ):
            resp = client.get("/api/v1/students/me/profile")
    finally:
        _clear()
    assert resp.status_code == 200
    assert resp.json()["student_id"] == row["student_id"]


def test_student_cannot_access_admin_operation():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        resp = client.get("/api/v1/admin/me")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_student_cannot_access_ingestion_operations():
    claims = {"sub": str(uuid4()), "email": "student@college.edu"}
    user = {
        "user_id": str(uuid4()),
        "auth_user_id": claims["sub"],
        "email": claims["email"],
        "roles": ["student"],
    }
    p1 = patch("app.core.security.verify_jwt", return_value=claims)
    p2 = patch(
        "app.db.supabase.get_user_by_auth_id",
        new=AsyncMock(return_value=user),
    )
    with p1, p2:
        r1 = client.post(
            "/api/v1/documents/ingest",
            headers={"Authorization": "Bearer student.token"},
        )
        r2 = client.post(
            f"/api/v1/documents/{RUN_ID}/chunk",
            headers={"Authorization": "Bearer student.token"},
        )
    assert (r1.status_code, r2.status_code) == (403, 403)


def test_student_cannot_approve_reject_or_manage():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
        r4 = client.get("/api/v1/admin/students")
        r5 = client.get("/api/v1/admin/audit-logs")
    finally:
        _clear()
    assert (r1.status_code, r2.status_code, r3.status_code) == (403, 403, 403)
    assert (r4.status_code, r5.status_code) == (403, 403)

def test_student_cannot_access_another_students_resource():
    user_a = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": str(uuid4()),
        "email": "user-a@college.edu",
        "roles": ["student"],
    }
    _as(user_a)
    try:
        with patch(
            "app.services.conversation_history.get_admin_client",
            return_value=MagicMock(),
        ), patch(
            "app.services.conversation_history.get_conversation",
            return_value={
                "conversation_id": str(uuid4()),
                "user_id": "10000000-0000-0000-0000-000000000002",
            },
        ):
            resp = client.get(f"/api/v1/conversations/{uuid4()}/messages")
    finally:
        _clear()
    assert resp.status_code == 404


def test_student_cannot_cross_tenant_via_chat():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        with patch("app.main.process_chat_request") as process:
            resp = client.post(
                "/api/v1/generation/chat",
                json={
                    "user_query": "What is the hostel fee?",
                    "institution_id": TENANT_B,
                },
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    process.assert_not_called()


def test_registration_rejects_client_role_fields():
    base = {
        "institution_id": TENANT_A,
        "email": "new@college.edu",
        "password": "secret123",
        "first_name": "New",
        "last_name": "Student",
        "register_number": "REG1",
    }
    for extra in (
        {"role": "admin"},
        {"roles": ["admin"]},
        {"approval_status": "approved"},
    ):
        resp = client.post("/api/v1/registration", json={**base, **extra})
        assert resp.status_code == 422, resp.text


def test_student_login_rejects_client_role_fields():
    base = {"identifier": "student@college.edu", "password": "password"}
    for extra in (
        {"role": "admin"},
        {"roles": ["admin"]},
        {"institution_id": TENANT_A},
        {"approval_status": "approved"},
        {"user_id": str(uuid4())},
        {"student_id": str(uuid4())},
    ):
        resp = client.post(
            "/api/v1/auth/student/login", json={**base, **extra}
        )
        assert resp.status_code == 422, (extra, resp.text)


def test_approval_body_tampering_is_inert():
    _as(_user(TENANT_A, roles=("admin",)))
    row = {"student_id": STUDENT_A, "approval_status": "approved"}
    try:
        with (
            patch(
                "app.api.admin.admin_academics.approve_student",
                return_value=row,
            ) as approve,
            patch("app.api.admin._record_audit"),
        ):
            resp = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/approve",
                json={
                    "role": "admin",
                    "institution_id": TENANT_B,
                    "approval_status": "approved",
                },
            )
    finally:
        _clear()
    assert resp.status_code == 200
    approve.assert_called_once()


def test_foreign_institution_id_query_is_rejected_for_bound_admin():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students"
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    list_students.assert_not_called()


def test_tenant_bound_user_cannot_access_foreign_tenant_object():
    _as(_user(TENANT_A, roles=("admin",)))
    foreign = {
        "student_id": STUDENT_A,
        "institution_id": TENANT_B,
        "student_number": "S1",
    }
    try:
        with patch(
            "app.api.admin.admin_academics.get_student", return_value=foreign
        ):
            resp = client.get(f"/api/v1/admin/students/{STUDENT_A}")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_forbidden_never_runs_protected_operation():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students"
        ) as list_students:
            resp = client.get("/api/v1/admin/students")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    list_students.assert_not_called()
