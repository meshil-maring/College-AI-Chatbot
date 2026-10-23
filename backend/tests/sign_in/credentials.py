"""Credentials."""

from __future__ import annotations

from supabase_auth.errors import AuthApiError

from typing import Any

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import json

from .support import (
    ACCOUNT_PASSWORD,
    APPROVED_EMAIL,
    INSTITUTION_CODE,
    LOGIN_URL,
    STUDENT_LOGIN_URL,
    _UNSET,
    client,
    institution_db,
    link_public_account,
    student_row,
)


def auth_client(
    student: dict | None = None,
    success: bool = True,
    user_email: str | None = None,
) -> MagicMock:
    """Supabase Auth (GoTrue) client mock — the single credential authority."""
    auth = MagicMock()
    if not success:
        auth.auth.sign_in_with_password.side_effect = AuthApiError(
            "Invalid login credentials", 400, "invalid_grant"
        )
        return auth
    session = MagicMock()
    session.access_token = "mock-access-token"
    session.refresh_token = "mock-refresh-token"
    session.expires_in = 3600
    user = MagicMock()
    user.id = str((student or {}).get("user_id", uuid4()))
    user.email = (student or {}).get("email") or user_email or APPROVED_EMAIL
    auth.auth.sign_in_with_password.return_value = MagicMock(session=session, user=user)
    return auth


def login_api(
    *,
    account: dict | None,
    auth: MagicMock | None = None,
    db: MagicMock | None = None,
    email: str = APPROVED_EMAIL,
    password: str = ACCOUNT_PASSWORD,
):
    """POST /api/v1/auth/login with the EXISTING flow patched end-to-end."""
    auth = auth or auth_client(user_email=email)
    db = db or institution_db()
    with (
        patch("app.api.auth.common.create_supabase_client", return_value=auth),
        patch(
            "app.api.auth.common.get_sign_in_context",
            new=AsyncMock(return_value=account),
        ),
        patch("app.api.auth.common.get_admin_client", return_value=db),
    ):
        return client.post(LOGIN_URL, json={"email": email, "password": password})


def student_login_api(
    *,
    student: dict | None,
    institution_code: str | None = None,
    identifier: str | None = None,
    password: str = ACCOUNT_PASSWORD,
    auth: MagicMock | None = None,
    db: MagicMock | None = None,
    institution: dict | None = None,
    by_register: Any = _UNSET,
    by_roll: Any = _UNSET,
    by_email: Any = _UNSET,
):
    """POST /api/v1/auth/student/login through the EXISTING Phase 6.5 flow.

    ``by_register`` / ``by_roll`` / ``by_email`` default to the student row
    (the happy path). Pass an explicit ``None`` to simulate "not found" inside
    that institution, which is how the wrong-institution-code and
    nonexistent-student cases are exercised.
    """
    auth = auth or auth_client(student)
    db = db or institution_db()
    student = student or student_row()
    link_public_account(db, student["user_id"])
    institution = institution or {
        "institution_id": str(student["institution_id"]),
        "name": "Test College",
        "code": institution_code or INSTITUTION_CODE,
        "status": "active",
        "is_active": True,
    }
    identifier = identifier if identifier is not None else student["email"]
    if by_email is _UNSET:
        by_email = student
    if by_register is _UNSET:
        by_register = student
    if by_roll is _UNSET:
        by_roll = student
    payload: dict[str, Any] = {"identifier": identifier, "password": password}
    if institution_code is not None:
        payload["institution_code"] = institution_code
    with (
        patch("app.services.auth.student_auth.get_admin_client", return_value=db),
        patch(
            "app.services.auth.student_auth.create_supabase_client", return_value=auth
        ),
        patch(
            "app.services.auth.student_auth._find_institution_by_code",
            return_value=institution,
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_email_global",
            return_value=by_email,
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_register_number",
            return_value=by_register,
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_university_roll_number",
            return_value=by_roll,
        ),
    ):
        return client.post(STUDENT_LOGIN_URL, json=payload)


def assert_student_failure(response) -> None:
    """All student-endpoint denials use the LOCKED 401 INVALID_CREDENTIALS contract."""
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    _assert_no_password_material(response)


def assert_login_failure(response) -> None:
    """All email-login denials use the LOCKED Phase 5.4 400 contract."""
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.json()["error"]["message"] == "Invalid login credentials"
    _assert_no_password_material(response)


def _assert_no_password_material(response) -> None:
    """The password value is NEVER echoed, and no password field is returned.

    The locked error MESSAGE legitimately contains the English word
    "password" (Supabase's own wording) — what must never appear is the
    submitted password value or a ``password`` response field.
    """
    body = response.json()
    assert ACCOUNT_PASSWORD not in response.text
    assert "password" not in json.dumps(body).lower().replace(
        '"invalid identifier or password"', ""
    )
    assert "password" not in json.dumps(body.get("user", {})).lower()


def _assert_no_secret(response, secret: str) -> None:
    assert secret not in response.text
    body = response.json()
    assert secret not in json.dumps(body)
    for value in body.values():
        assert value != secret
    if isinstance(body.get("user"), dict):
        for value in body["user"].values():
            assert value != secret
