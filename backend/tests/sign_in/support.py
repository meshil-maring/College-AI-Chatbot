"""Support."""

from __future__ import annotations

from app.main import app

from fastapi.testclient import TestClient

from supabase import Client

from typing import Any

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4


client = TestClient(app, raise_server_exceptions=False)


INSTITUTION_A = uuid4()


INSTITUTION_B = uuid4()


INSTITUTION_CODE = "GIT"


ORGANIZATION_ID = uuid4()


ACCOUNT_PASSWORD = "correct-horse-battery"


APPROVED_EMAIL = "approved@college.edu"


APPROVED_REGISTER = "REG2026001"


APPROVED_ROLL = "UR2026001"


STUDENT_B = uuid4()


LOGIN_URL = "/api/v1/auth/login"


STUDENT_LOGIN_URL = "/api/v1/auth/student/login"


def student_row(**overrides: Any) -> dict:
    """A ``students`` identity row as returned by the existing repositories."""
    return {
        "student_id": uuid4(),
        "user_id": uuid4(),
        "institution_id": INSTITUTION_A,
        "email": APPROVED_EMAIL,
        "register_number": APPROVED_REGISTER,
        "university_roll_number": APPROVED_ROLL,
        "approval_status": "approved",
        "is_active": True,
        "status": "active",
        **overrides,
    }


def sign_in_account(**overrides: Any) -> dict:
    """The server-resolved context returned by ``get_sign_in_context``.

    Mirrors the real projection exactly:
    ``{user_id, status, institution_id, approval_status, student_is_active}``.
    """
    account = {
        "user_id": str(uuid4()),
        "status": "active",
        "institution_id": None,
        "approval_status": None,
        "student_is_active": None,
    }
    account.update(overrides)
    return account


def student_account(**overrides: Any) -> dict:
    """An approved + active student account (tenant-bound)."""
    account = sign_in_account(
        institution_id=str(INSTITUTION_A),
        approval_status="approved",
        student_is_active=True,
    )
    account.update(overrides)
    return account


def institution_db(
    is_active: bool = True, code: str = INSTITUTION_CODE, auth_user_id=None
) -> MagicMock:
    """Admin client mock whose institution lookup returns one row."""
    db = MagicMock(spec=Client)
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data
    ) = {
        "institution_id": str(INSTITUTION_A),
        "name": "Test College",
        "code": code,
        "status": "active" if is_active else "pending",
        "is_active": is_active,
    }
    if auth_user_id is not None:
        link_public_account(db, auth_user_id)
    return db


def link_public_account(db, auth_user_id):
    """Keep institution and application-account reads separate in the fixture."""
    institution_query = db.table.return_value
    user_query = MagicMock()
    user_query.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "auth_user_id": str(auth_user_id),
        "status": "active",
    }
    db.table.side_effect = lambda name: (
        user_query if name == "users" else institution_query
    )


_UNSET = object()


FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "person@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}


FACULTY_EMAIL = "faculty@college.edu"


STAFF_EMAIL = "staff@college.edu"


ADMIN_EMAIL = "admin@college.edu"


SECRET_PASSWORD = "Sup3rSecret-Login-Pass!"
