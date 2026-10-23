"""Test student identity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    STUDENT_A,
    TENANT_A,
    TENANT_B,
    _as,
    _clear,
    _user,
    client,
)


def test_05_student_isolation_on_admin_and_chat_and_own_data():
    """A student never reaches admin data, foreign tenants, or foreign rows."""
    student = _user(TENANT_A, roles=("student",))
    # Admin boundary closed.
    _as(student)
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals"
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_A}"
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        list_students.assert_not_called()

        # Chat: client-supplied foreign institution rejected server-side.
        with patch("app.main.process_chat_request") as process:
            resp = client.post(
                "/api/v1/generation/chat",
                json={"user_query": "hi", "institution_id": TENANT_B},
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        process.assert_not_called()

        # Own-profile read whose row points at ANOTHER tenant fails closed.
        foreign_profile = {
            "student_id": STUDENT_A,
            "user_id": student["user_id"],
            "institution_id": TENANT_B,
        }
        db = MagicMock()
        (
            db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
        ).return_value = MagicMock(data=foreign_profile)
        with patch(
            "app.services.students.student_data.get_admin_client", return_value=db
        ):
            resp = client.get("/api/v1/students/me/profile")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    finally:
        _clear()


def test_05b_student_same_tenant_data_allowed():
    """A student of Institution A reads their own Institution A profile."""
    student = _user(TENANT_A, roles=("student",))
    own_profile = {
        "student_id": STUDENT_A,
        "user_id": student["user_id"],
        "institution_id": TENANT_A,
    }
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=own_profile)
    _as(student)
    try:
        with patch(
            "app.services.students.student_data.get_admin_client", return_value=db
        ):
            resp = client.get("/api/v1/students/me/profile")
    finally:
        _clear()
    assert resp.status_code == 200
    assert "institution_id" not in resp.json()
