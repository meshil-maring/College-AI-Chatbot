"""Test request validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4

from .support import (
    STUDENT_A,
    TENANT_A,
    TENANT_B,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


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
        resp = client.post("/api/v1/auth/student/login", json={**base, **extra})
        assert resp.status_code == 422, (extra, resp.text)


def test_approval_body_tampering_is_inert():
    _as(_user(TENANT_A, roles=("admin",)))
    row = {"student_id": STUDENT_A, "approval_status": "approved"}
    try:
        with (
            patch(
                "app.services.admin.admin_academics.approve_student",
                return_value=row,
            ) as approve,
            patch("app.api.admin.common.record_audit"),
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
