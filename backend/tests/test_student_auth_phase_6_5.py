"""Phase 6.5 - Student Authentication Tests.

Tests the student login endpoint covering:
- Email login (globally unique)
- Academic identifier login (institution-scoped, requires institution_code)
- Cross-tenant ambiguity prevention
- Approval/lifecycle enforcement
- Security (no enumeration, no escalation, no client-controlled fields)
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from supabase import Client
from supabase_auth.errors import AuthApiError

from app.main import app
from app.services.student_auth import (
    SafeAuthFailure,
    _assert_approved,
    _assert_institution_active,
    _assert_student_active,
    _is_email,
    _resolve_by_email,
    _resolve_identity,
    authenticate_student,
)

client = TestClient(app, raise_server_exceptions=False)
logger = logging.getLogger(__name__)

APPROVED_EMAIL = "approved@college.edu"
APPROVED_REGISTER = "REG2026001"
APPROVED_ROLL = "UR2026001"
INSTITUTION_CODE = "GIT"
INSTITUTION_A = uuid4()
INSTITUTION_B = uuid4()


def approved_student(**overrides: Any) -> dict:
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


def _inst_response(institution_id=None, code=INSTITUTION_CODE, is_active=True):
    return {
        "institution_id": institution_id or INSTITUTION_A,
        "name": "Test College",
        "code": code,
        "is_active": is_active,
    }


def make_mocks(student, auth_success=True, institution_active=True):
    mocks = {}
    db = MagicMock(spec=Client)
    mocks["db"] = db
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = _inst_response(institution_id=student.get("institution_id"), is_active=institution_active)
    auth_client = MagicMock()
    mocks["auth_client"] = auth_client
    if auth_success:
        session = MagicMock()
        session.access_token = "mock-access-token"
        mock_user = MagicMock()
        mock_user.id = str(student["user_id"])
        mock_user.email = student["email"]
        auth_client.auth.sign_in_with_password.return_value = MagicMock(session=session, user=mock_user)
    else:
        auth_client.auth.sign_in_with_password.side_effect = AuthApiError("Invalid", 400, "invalid_grant")
    return mocks


class TestIsEmail:
    def test_email_detected(self):
        assert _is_email("student@college.edu") is True

    def test_non_email_not_detected(self):
        assert _is_email("REG2026001") is False


@pytest.mark.asyncio
async def test_resolve_by_email_found():
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        result = _resolve_by_email(db, student["email"])
    assert result is not None


@pytest.mark.asyncio
async def test_resolve_by_email_not_found():
    db = MagicMock(spec=Client)
    with patch("app.repositories.admin_academics.get_student_by_email_global", return_value=None):
        result = _resolve_by_email(db, "nonexistent@college.edu")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_identity_academic_id_requires_institution_code():
    db = MagicMock(spec=Client)
    result = _resolve_identity(db, APPROVED_REGISTER, None)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_identity_email_ignores_institution_code():
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth._resolve_by_email",
               return_value=(student["email"].lower(), student["institution_id"], student)):
        result = _resolve_identity(db, student["email"], INSTITUTION_CODE)
    assert result is not None


def test_assert_approved_passes():
    _assert_approved(approved_student(approval_status="approved"))


def test_assert_approved_pending():
    with pytest.raises(SafeAuthFailure):
        _assert_approved(approved_student(approval_status="pending"))


def test_assert_student_active_passes():
    _assert_student_active(approved_student(is_active=True))


def test_assert_student_active_inactive():
    with pytest.raises(SafeAuthFailure):
        _assert_student_active(approved_student(is_active=False))


def test_assert_institution_active_passes():
    db = MagicMock(spec=Client)
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {"institution_id": INSTITUTION_A, "is_active": True}
    _assert_institution_active(db, INSTITUTION_A)


def test_assert_institution_active_inactive():
    db = MagicMock(spec=Client)
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {"institution_id": INSTITUTION_A, "is_active": False}
    with pytest.raises(SafeAuthFailure):
        _assert_institution_active(db, INSTITUTION_A)


@pytest.mark.asyncio
async def test_authenticate_email_success():
    """A. Valid email + correct password."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        result = authenticate_student(APPROVED_EMAIL, "correct_password")
    assert result["access_token"] == "mock-access-token"


@pytest.mark.asyncio
async def test_authenticate_email_wrong_password():
    """B. Valid email + wrong password."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=False)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "wrong_password")


@pytest.mark.asyncio
async def test_authenticate_register_number_success():
    """C. Valid register number + correct password (with institution_code)."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=student), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=None):
        result = authenticate_student(APPROVED_REGISTER, "correct_password", INSTITUTION_CODE)
    assert result["access_token"] == "mock-access-token"


@pytest.mark.asyncio
async def test_authenticate_register_number_wrong_password():
    """D. Valid register number + wrong password."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=False)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=student), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=None):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_REGISTER, "wrong_password", INSTITUTION_CODE)


@pytest.mark.asyncio
async def test_authenticate_roll_number_success():
    """E. Valid university roll number + correct password (with institution_code)."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=None), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=student):
        result = authenticate_student(APPROVED_ROLL, "correct_password", INSTITUTION_CODE)
    assert result["access_token"] == "mock-access-token"


@pytest.mark.asyncio
async def test_authenticate_roll_number_wrong_password():
    """F. Valid university roll number + wrong password."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=False)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=None), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_ROLL, "wrong_password", INSTITUTION_CODE)


@pytest.mark.asyncio
async def test_authenticate_unknown_identifier():
    """G. Unknown identifier."""
    with patch("app.services.student_auth.get_admin_client", return_value=MagicMock(spec=Client)), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=None):
        with pytest.raises(SafeAuthFailure):
            authenticate_student("unknown@college.edu", "password")


@pytest.mark.asyncio
async def test_authenticate_empty_identifier():
    """H. Empty identifier."""
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db):
        with pytest.raises(SafeAuthFailure):
            authenticate_student("", "password")


@pytest.mark.asyncio
async def test_authenticate_empty_password():
    """J. Empty password."""
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "")


@pytest.mark.asyncio
async def test_authenticate_pending_student():
    """K. Pending student blocked."""
    student = approved_student(approval_status="pending")
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._assert_institution_active"), \
         patch("app.services.student_auth._supabase_sign_in") as mock_signin, \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "password")
    mock_signin.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_rejected_student():
    """L. Rejected student blocked."""
    student = approved_student(approval_status="rejected")
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._assert_institution_active"), \
         patch("app.services.student_auth._supabase_sign_in") as mock_signin, \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "password")
    mock_signin.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_inactive_student():
    """M. Inactive student blocked."""
    student = approved_student(is_active=False)
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._assert_institution_active"), \
         patch("app.services.student_auth._supabase_sign_in") as mock_signin, \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "password")
    mock_signin.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_inactive_institution():
    """N. Inactive institution blocked."""
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._supabase_sign_in") as mock_signin, \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student), \
         patch("app.services.student_auth._assert_institution_active", side_effect=SafeAuthFailure):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_EMAIL, "password")
    mock_signin.assert_not_called()


@pytest.mark.asyncio
async def test_same_register_number_different_institutions_no_cross_auth():
    """A. Same register number in two institutions cannot cause incorrect authentication."""
    student_git = approved_student(
        institution_id=INSTITUTION_A,
        register_number=APPROVED_REGISTER,
        email="git_student@college.edu",
    )
    mocks = make_mocks(student_git, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=student_git), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=None):
        result = authenticate_student(APPROVED_REGISTER, "password", INSTITUTION_CODE)
    assert result["user"]["email"] == "git_student@college.edu"


@pytest.mark.asyncio
async def test_same_roll_number_different_institutions_no_cross_auth():
    """B. Same university roll number in two institutions cannot cause incorrect authentication."""
    student_git = approved_student(
        institution_id=INSTITUTION_A,
        university_roll_number=APPROVED_ROLL,
        email="git_student@college.edu",
    )
    mocks = make_mocks(student_git, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.services.student_auth._find_institution_by_code", return_value=_inst_response(institution_id=INSTITUTION_A)), \
         patch("app.repositories.admin_academics.get_student_by_register_number", return_value=None), \
         patch("app.repositories.admin_academics.get_student_by_university_roll_number", return_value=student_git):
        result = authenticate_student(APPROVED_ROLL, "password", INSTITUTION_CODE)
    assert result["user"]["email"] == "git_student@college.edu"


@pytest.mark.asyncio
async def test_wrong_institution_code_cannot_authenticate():
    """D. Wrong institution_code cannot authenticate."""
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._find_institution_by_code", return_value=None):
        with pytest.raises(SafeAuthFailure):
            authenticate_student(APPROVED_REGISTER, "password", "WRONG")


@pytest.mark.asyncio
async def test_email_login_globally_deterministic():
    """E. Email login remains globally deterministic."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        result = authenticate_student(APPROVED_EMAIL, "password")
    assert result["access_token"] == "mock-access-token"


@pytest.mark.asyncio
async def test_api_academic_id_login_requires_institution_code():
    """I. Academic identifier without institution_code returns validation failure."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={"identifier": APPROVED_REGISTER, "password": "password"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_email_login_works_without_institution_code():
    """B. Email + password works without institution_code."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=True)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": APPROVED_EMAIL, "password": "password"},
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "mock-access-token"


def test_api_rejects_client_institution_id():
    """Q. No client-controlled internal institution_id is accepted."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "identifier": APPROVED_EMAIL,
            "password": "password",
            "institution_id": str(uuid4()),
        },
    )
    assert response.status_code == 422


def test_api_rejects_client_role():
    """Q. No client-controlled role is accepted."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "identifier": APPROVED_EMAIL,
            "password": "password",
            "role": "admin",
        },
    )
    assert response.status_code == 422


def test_api_rejects_client_approval_status():
    """Q. No client-controlled approval_status is accepted."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "identifier": APPROVED_EMAIL,
            "password": "password",
            "approval_status": "approved",
        },
    )
    assert response.status_code == 422


def test_api_rejects_client_user_id():
    """Q. No client-controlled user_id is accepted."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "identifier": APPROVED_EMAIL,
            "password": "password",
            "user_id": str(uuid4()),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_login_malformed_input_missing_fields():
    """Malformed input - missing fields."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={"identifier": APPROVED_EMAIL},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_login_malformed_input_extra_fields():
    """Malformed input - unexpected fields."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={
            "identifier": APPROVED_EMAIL,
            "password": "password",
            "unexpected_field": "value",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_login_empty_identifier():
    """Empty identifier."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={"identifier": "", "password": "password"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_login_empty_password():
    """Empty password."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={"identifier": APPROVED_EMAIL, "password": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_login_unknown_identifier_returns_401():
    """Unknown identifier returns 401 (not 404)."""
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=None):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": "nobody@college.edu", "password": "password"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_wrong_password_returns_401():
    """Wrong password returns 401 with safe message."""
    student = approved_student()
    mocks = make_mocks(student, auth_success=False)
    db = mocks["db"]
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client", return_value=mocks["auth_client"]), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": APPROVED_EMAIL, "password": "wrongpassword"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_pending_student_returns_401():
    """Pending student cannot authenticate - no enumeration."""
    student = approved_student(approval_status="pending")
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._assert_institution_active"), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": APPROVED_EMAIL, "password": "password"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_rejected_student_returns_401():
    """Rejected student cannot authenticate - no enumeration."""
    student = approved_student(approval_status="rejected")
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth._assert_institution_active"), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": APPROVED_EMAIL, "password": "password"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_unknown_institution_code_returns_401():
    """Unknown institution_code fails safely for academic identifier."""
    response = client.post(
        "/api/v1/auth/student/login",
        json={"identifier": APPROVED_REGISTER, "password": "password", "institution_code": "UNKNOWN"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_admin_credentials_not_student():
    """Admin/staff credentials cannot misuse student login endpoint."""
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=None):
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": "admin@college.edu", "password": "adminpass"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_login_supabase_auth_failure():
    """Supabase Auth failure is normalized to safe 401."""
    student = approved_student()
    db = MagicMock(spec=Client)
    with patch("app.services.student_auth.get_admin_client", return_value=db), \
         patch("app.services.student_auth.create_supabase_client") as mock_create, \
         patch("app.repositories.admin_academics.get_student_by_email_global", return_value=student):
        auth_client = MagicMock()
        auth_client.auth.sign_in_with_password.side_effect = AuthApiError("Auth error", 400, "invalid_grant")
        mock_create.return_value = auth_client
        response = client.post(
            "/api/v1/auth/student/login",
            json={"identifier": APPROVED_EMAIL, "password": "password"},
        )
    assert response.status_code == 401
