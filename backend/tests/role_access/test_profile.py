"""Test profile."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4

from .support import (
    RUN_ID,
    STUDENT_A,
    TENANT_A,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


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
            "app.services.students.student_data.get_admin_client", return_value=db
        ):
            resp = client.get("/api/v1/students/me/profile")
    finally:
        _clear()
    assert resp.status_code == 200
    assert "student_id" not in resp.json()


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
    user = _user(TENANT_A, roles=("student",))
    user.update(
        auth_user_id=claims["sub"],
        email=claims["email"],
        permissions_resolved=True,
        scoped_permissions_resolved=True,
    )
    user["role_assignments"][0]["permissions"] = ["profile.own.read"]
    p1 = patch("app.core.security.tokens.verify_jwt", return_value=claims)
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
    assert (r4.status_code, r5.status_code) == (404, 403)


def test_student_cannot_access_another_students_resource():
    user_a = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": str(uuid4()),
        "email": "user-a@college.edu",
        "roles": ["student"],
    }
    _as(user_a)
    try:
        with (
            patch(
                "app.services.ai.conversation_history.get_admin_client",
                return_value=MagicMock(),
            ),
            patch(
                "app.services.ai.conversation_history.get_conversation",
                return_value={
                    "conversation_id": str(uuid4()),
                    "user_id": "10000000-0000-0000-0000-000000000002",
                },
            ),
        ):
            resp = client.get(f"/api/v1/conversations/{uuid4()}/messages")
    finally:
        _clear()
    assert resp.status_code == 404
