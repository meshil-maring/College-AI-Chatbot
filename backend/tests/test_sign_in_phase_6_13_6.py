"""Phase 6.13.6 — Multi-Identifier Sign In tests.

Covers the Phase 6.13.6 requirements:

    * student email login
    * student register-number login (institution_code required)
    * student university-roll-number login (institution_code required)
    * wrong institution code for both academic identifiers
    * nonexistent student / wrong password
    * pending user / rejected user / inactive institution / pending institution
    * approved + active student
    * faculty login / staff login / admin login compatibility
    * role cannot be overridden
    * institution scope cannot be overridden
    * organization scope cannot be overridden
    * cross-institution access denied
    * tenant resolution after login
    * invalid login input
    * password never returned / never logged / never stored
    * existing Phase 6 login regression
    * Phase 6.13.1-6.13.5 regression

No new authentication system: every test exercises the EXISTING Supabase Auth
credential flow, the EXISTING student login endpoint (Phase 6.5), the EXISTING
email login endpoint (Phase 5.4 / 6.x), and the Phase 6.13.6 status guard.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from supabase import Client
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.core.security import assert_tenant_object, scope_tenant
from app.db.supabase import get_sign_in_context, get_user_by_auth_id
from app.main import app
from app.services.sign_in import _has_student_profile, assert_sign_in_allowed
from app.services.student_auth import SafeAuthFailure

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


# ---------------------------------------------------------------------------
# Helpers — trusted server-side records (never client-supplied)
# ---------------------------------------------------------------------------


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


def institution_db(is_active: bool = True, code: str = INSTITUTION_CODE) -> MagicMock:
    """Admin client mock whose institution lookup returns one row."""
    db = MagicMock(spec=Client)
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single
        .return_value.execute.return_value.data
    ) = {
        "institution_id": str(INSTITUTION_A),
        "name": "Test College",
        "code": code,
        "status": "active" if is_active else "pending",
        "is_active": is_active,
    }
    return db


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
    with patch("app.api.auth.create_supabase_client", return_value=auth), patch(
        "app.api.auth.get_sign_in_context", new=AsyncMock(return_value=account)
    ), patch("app.api.auth.get_admin_client", return_value=db):
        return client.post(LOGIN_URL, json={"email": email, "password": password})


_UNSET = object()


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
    with patch("app.services.student_auth.get_admin_client", return_value=db), patch(
        "app.services.student_auth.create_supabase_client", return_value=auth
    ), patch(
        "app.services.student_auth._find_institution_by_code", return_value=institution
    ), patch(
        "app.repositories.admin_academics.get_student_by_email_global",
        return_value=by_email,
    ), patch(
        "app.repositories.admin_academics.get_student_by_register_number",
        return_value=by_register,
    ), patch(
        "app.repositories.admin_academics.get_student_by_university_roll_number",
        return_value=by_roll,
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


# ===========================================================================
# 1-3. Student sign-in — all three existing login methods preserved
# ===========================================================================


def test_01_student_email_login_succeeds():
    """Email + password needs no institution context (globally unique)."""
    student = student_row()
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"] == "mock-access-token"
    assert body["message"] == "Login successful."
    assert body["user"]["email"] == APPROVED_EMAIL


def test_02_student_register_number_login_succeeds():
    """Register number + password + institution_code."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


def test_03_student_university_roll_number_login_succeeds():
    """University roll number + password + institution_code."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_ROLL,
        institution_code=INSTITUTION_CODE,
        by_register=None,
        by_roll=student,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


def test_04_register_number_wrong_institution_code_denied():
    """The institution code scopes the lookup — a wrong code finds nobody."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code="WRONG",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "WRONG",
            "status": "active",
            "is_active": True,
        },
        by_register=None,
        by_roll=None,
    )
    assert_student_failure(response)


def test_05_roll_number_wrong_institution_code_denied():
    """Same fail-closed scoping for the university roll number path."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_ROLL,
        institution_code="WRONG",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "WRONG",
            "status": "active",
            "is_active": True,
        },
        by_register=None,
        by_roll=None,
    )
    assert_student_failure(response)


def test_06_nonexistent_student_denied():
    """Unknown identifier -> generic credentials failure (never 404)."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier="does-not-exist@college.edu",
        by_email=None,
    )
    # Phase 6.5 contract: the student endpoint normalizes every failure to the
    # SafeAuthFailure envelope (401 INVALID_CREDENTIALS); existence is never
    # disclosed and 404 is never returned.
    assert_student_failure(response)


def test_07_wrong_password_denied():
    """Supabase Auth rejects the credential — no session is issued."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_EMAIL,
        password="wrong-password",
        auth=auth_client(student, success=False),
    )
    assert_student_failure(response)

# ===========================================================================
# 8-12. Account + institution status (fail-closed)
# ===========================================================================


def test_08_pending_user_sign_in_denied():
    """PENDING student (approval_status='pending') cannot sign in."""
    student = student_row(approval_status="pending")
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_09_rejected_user_sign_in_denied():
    """REJECTED student (approval_status='rejected') cannot sign in."""
    student = student_row(approval_status="rejected")
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_09b_inactive_student_profile_sign_in_denied():
    """A lifecycle-inactive students profile cannot sign in."""
    student = student_row(is_active=False)
    response = student_login_api(student=student, identifier=APPROVED_EMAIL)
    assert response.status_code == 401, response.text


def test_10_inactive_institution_denied():
    """is_active=False institution -> protected access denied."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_EMAIL,
        db=institution_db(is_active=False),
    )
    assert response.status_code == 401, response.text


def test_11_pending_institution_denied():
    """status='pending' institution (is_active=False) -> denied."""
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        institution={
            "institution_id": str(INSTITUTION_A),
            "name": "Pending College",
            "code": INSTITUTION_CODE,
            "status": "pending",
            "is_active": False,
        },
        db=institution_db(is_active=False),
        by_register=student,
    )
    assert response.status_code == 401, response.text


def test_12_approved_active_student_succeeds():
    """ACTIVE user + ACTIVE institution -> normal authenticated access."""
    student = student_row(approval_status="approved", is_active=True)
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


# ---------------------------------------------------------------------------
# Email login status guard (POST /api/v1/auth/login) — same rules, fail-closed
# ---------------------------------------------------------------------------


def test_08b_pending_user_email_login_denied():
    account = student_account(approval_status="pending")
    assert_login_failure(login_api(account=account, db=institution_db(is_active=True)))


def test_09c_rejected_user_email_login_denied():
    account = student_account(approval_status="rejected")
    assert_login_failure(login_api(account=account, db=institution_db(is_active=True)))


def test_10b_inactive_institution_email_login_denied():
    account = student_account()
    assert_login_failure(login_api(account=account, db=institution_db(is_active=False)))


def test_11b_pending_institution_email_login_denied():
    account = student_account()
    assert_login_failure(login_api(account=account, db=institution_db(is_active=False)))


def test_12b_active_student_email_login_succeeds():
    response = login_api(account=student_account(), db=institution_db(is_active=True))
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"
    assert response.json()["message"] == "Login successful."


def test_12c_missing_public_users_row_denied():
    """No public.users row -> no application account -> sign-in denied."""
    assert_login_failure(login_api(account=None))


def test_12d_non_active_users_status_denied():
    """users.status values other than 'active' are denied (fail-closed)."""
    for status in ("inactive", "deactivated", None, "unknown"):
        assert_login_failure(login_api(account=sign_in_account(status=status)))
# ===========================================================================
# 13-15. Faculty / staff / admin compatibility (existing identity fields only)
# ===========================================================================
# Phase 6.13.5 registers faculty and staff with the SAME existing identity
# fields as students — public.users.email + Supabase Auth password. No new
# login identifier is invented. After approval the role is granted server-side
# (institution scope); protected access then follows the existing Phase 6.6 RBAC.


def _auth_user(user: dict, roles: tuple[str, ...], institution_id=None) -> dict:
    """The ``get_user_by_auth_id`` projection for a non-student account."""
    return {
        "user_id": str(user["user_id"]),
        "auth_user_id": user["auth_user_id"],
        "email": user["email"],
        "roles": list(roles),
        "institution_id": str(institution_id) if institution_id else None,
    }


def _as_authenticated(fake_user: dict):
    """Patch JWT verification + public.users resolution (existing Phase 6)."""
    return (
        patch("app.core.security.verify_jwt", return_value=FAKE_CLAIMS),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=fake_user),
        ),
    )


FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "person@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FACULTY_EMAIL = "faculty@college.edu"
STAFF_EMAIL = "staff@college.edu"
ADMIN_EMAIL = "admin@college.edu"


def test_13_faculty_login_succeeds_with_existing_email_identity():
    """Faculty sign in with the existing email + password identity model."""
    response = login_api(
        account=sign_in_account(status="active"),
        email=FACULTY_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "mock-access-token"


def test_13b_pending_faculty_has_no_role_so_protected_access_denied():
    """Pending faculty hold NO role yet (Phase 6.13.5) -> 403 FORBIDDEN."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": FACULTY_EMAIL}
    verify, db = _as_authenticated(_auth_user(user, roles=(), institution_id=INSTITUTION_A))
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_13c_approved_faculty_role_resolved_server_side():
    """Once approved, the 'faculty' role comes from trusted records only."""
    import asyncio

    from app.core.security import require_roles

    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FACULTY_EMAIL,
        "roles": ["faculty"],
        "institution_id": str(INSTITUTION_A),
    }
    # Faculty passes the existing ingestion RBAC (admin/staff/faculty)...
    allowed = require_roles("admin", "staff", "faculty")
    assert asyncio.run(allowed(current_user=user)) is user
    # ...and is still denied the admin-only boundary (no escalation).
    denied = require_roles("admin")
    with pytest.raises(AppError) as exc:
        asyncio.run(denied(current_user=user))
    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"


def test_14_staff_login_succeeds_with_existing_email_identity():
    response = login_api(
        account=sign_in_account(status="active"),
        email=STAFF_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text


def test_14b_pending_staff_has_no_role_so_protected_access_denied():
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": STAFF_EMAIL}
    verify, db = _as_authenticated(_auth_user(user, roles=(), institution_id=INSTITUTION_A))
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 403


def test_14c_approved_staff_role_resolved_server_side():
    """Staff role + institution scope come from trusted records, not the client."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": STAFF_EMAIL}
    projection = _auth_user(user, roles=("staff",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db, patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ) as listing:
        response = client.get(
            "/api/v1/admin/students/pending",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    # The staff member's OWN institution was used as the tenant — never a
    # client-supplied value.
    assert UUID(str(listing.call_args.args[0])) == INSTITUTION_A


def test_15_admin_login_remains_compatible():
    """Existing admin authentication keeps working (Phase 5.4 / 6.6 intact)."""
    response = login_api(
        account=sign_in_account(status="active"),
        email=ADMIN_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == ADMIN_EMAIL

    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": ADMIN_EMAIL}
    verify, db = _as_authenticated(_auth_user(user, roles=("admin",)))
    with verify, db:
        me = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert me.status_code == 200, me.text
    assert me.json()["is_admin"] is True
    assert me.json()["roles"] == ["admin"]
# ===========================================================================
# 16-18. Authorization boundary — role / institution scope / organization scope
#        can NEVER be supplied or overridden by the client
# ===========================================================================


def _login_payload(url: str) -> dict:
    if url == LOGIN_URL:
        return {"email": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD}
    return {"identifier": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD}


def test_16_role_cannot_be_overridden_on_email_login():
    response = client.post(
        LOGIN_URL,
        json={"email": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD, "role": "admin"},
    )
    assert response.status_code == 422, response.text


def test_16b_role_cannot_be_overridden_on_student_login():
    response = client.post(
        STUDENT_LOGIN_URL,
        json={
            "identifier": APPROVED_EMAIL,
            "password": ACCOUNT_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 422, response.text


def test_16c_other_authorization_fields_cannot_be_overridden():
    for field, value in (
        ("roles", ["admin"]),
        ("status", "active"),
        ("approval_status", "approved"),
        ("is_admin", True),
        ("user_id", str(uuid4())),
        ("auth_user_id", str(uuid4())),
    ):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = value
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_16d_login_response_never_echoes_role_or_scope():
    response = login_api(account=student_account())
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"access_token", "message", "user"}
    assert set(body["user"].keys()) == {"id", "email"}


def test_16e_self_declared_role_is_ignored_by_rbac():
    """A client-declared role has no effect: RBAC reads trusted records."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": "x@c.edu"}
    projection = _auth_user(user, roles=(), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            "/api/v1/admin/me",
            headers={"Authorization": "Bearer valid.token.here", "X-Role": "admin"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_17_institution_scope_cannot_be_overridden():
    for field in ("institution_id", "scope_type", "scope_id"):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = str(INSTITUTION_B) if field != "scope_type" else "platform"
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_17b_tenant_bound_admin_cannot_request_foreign_institution():
    """Tenant scope is enforced by the locked Phase 6 scope_tenant guard."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": ADMIN_EMAIL}
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            f"/api/v1/admin/students/pending?institution_id={INSTITUTION_B}",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_17c_tenant_bound_admin_own_institution_is_scoped_not_substituted():
    """Same institution -> allowed, and the effective tenant is the caller's."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": ADMIN_EMAIL}
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db, patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ) as listing:
        response = client.get(
            f"/api/v1/admin/students/pending?institution_id={INSTITUTION_A}",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    assert UUID(str(listing.call_args.args[0])) == INSTITUTION_A
def test_18_organization_scope_cannot_be_overridden():
    for field in ("organization_id", "organization", "scope_organization_id"):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = str(ORGANIZATION_ID)
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_18b_organization_scope_comes_from_user_roles_only():
    """Client-declared scope fields are ignored; user_roles is authoritative."""
    from app.services.authorization import INSTITUTION, resolve_authorization_context

    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
        "institution_id": str(INSTITUTION_A),
        # Deliberately client-ish injected values that MUST be ignored.
        "roles": ["admin"],
        "scope_type": "platform",
        "scope_id": str(ORGANIZATION_ID),
        "organization_id": str(ORGANIZATION_ID),
    }
    rows = [
        {
            "role_id": uuid4(),
            "role_name": "admin",
            "is_active": True,
            "scope_type": INSTITUTION,
            "scope_id": str(INSTITUTION_A),
            "scope_organization_id": str(ORGANIZATION_ID),
        }
    ]
    with patch(
        "app.services.authorization.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.repositories.tenancy.get_user_role_scope_rows", return_value=rows
    ), patch(
        "app.repositories.tenancy.get_institution_organization",
        return_value=ORGANIZATION_ID,
    ):
        context = resolve_authorization_context(user)

    # The stored institution scope wins over the client-declared platform scope.
    assert context["scope_type"] == INSTITUTION
    assert UUID(context["scope_id"]) == INSTITUTION_A
    assert UUID(context["institution_id"]) == INSTITUTION_A
    assert UUID(context["organization_id"]) == ORGANIZATION_ID
    assert context["roles"] == ["admin"]


# ===========================================================================
# 19. Cross-institution access denied
# ===========================================================================


def test_19_cross_institution_access_denied():
    """Institution A staff cannot reach institution B student records."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": STAFF_EMAIL}
    projection = _auth_user(user, roles=("staff",), institution_id=INSTITUTION_A)
    target = {
        "student_id": str(STUDENT_B),
        "institution_id": str(INSTITUTION_B),
        "approval_status": "pending",
    }
    verify, db = _as_authenticated(projection)
    with verify, db, patch(
        "app.services.admin_academics.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.repositories.admin_academics.get_student_for_approval",
        return_value=target,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_19b_cross_institution_login_requires_correct_institution_code():
    """An academic identifier only resolves inside its own institution."""
    response = student_login_api(
        student=None,  # not present in the OTHER institution
        identifier=APPROVED_REGISTER,
        institution_code="OTHER-CODE",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "OTHER-CODE",
            "status": "active",
            "is_active": True,
        },
        db=institution_db(),
        by_register=None,
        by_roll=None,
    )
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_19c_cross_institution_student_lookup_uses_scoped_query():
    """The repository lookup is always filtered by institution_id."""
    from app.repositories import admin_academics as academics_repo

    db = MagicMock()
    table = MagicMock()
    db.table.return_value = table
    for method in ("select", "eq", "limit", "maybe_single", "execute"):
        getattr(table, method).return_value = table
    table.execute.return_value = SimpleNamespace(data=None)

    academics_repo.get_student_by_register_number(db, INSTITUTION_A, "REG-1")

    scoped = {call.args[0] for call in table.eq.call_args_list}
    assert scoped == {"institution_id", "register_number"}
# ===========================================================================
# 20. Tenant resolution after login
# ===========================================================================


def test_20a_tenant_resolution_after_email_login():
    """After email login the student profile is resolved server-side from the JWT.

    ``get_current_user`` (JWT ``sub`` -> ``get_user_by_auth_id``) supplies the
    tenant; the endpoint then asserts the returned profile belongs to that same
    tenant. Nothing tenant-related is accepted from the client.
    """
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": APPROVED_EMAIL}
    projection = _auth_user(user, roles=("student",), institution_id=INSTITUTION_A)
    profile = {"student_id": str(STUDENT_B), "institution_id": str(INSTITUTION_A)}
    verify, db = _as_authenticated(projection)
    with verify, db, patch(
        "app.api.students.student_data.get_own_profile", return_value=profile
    ) as get_profile:
        response = client.get(
            "/api/v1/students/me/profile",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["institution_id"] == str(INSTITUTION_A)
    # The profile was resolved from the JWT-derived user_id, never a client id.
    assert UUID(str(get_profile.call_args.args[0])) == UUID(str(user["user_id"]))


def test_20b_tenant_resolution_after_academic_identifier_login():
    """Register-number login resolves the student + tenant server-side.

    The response shape is the LOCKED Phase 6.5 contract (``access_token`` /
    ``message`` / ``user``); internal tenant/student ids are never exposed.
    """
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"access_token", "message", "user"}
    assert body["user"]["email"] == APPROVED_EMAIL
    assert str(INSTITUTION_A) not in response.text
    assert str(student["student_id"]) not in response.text


def test_20c_authorization_context_resolves_scope_from_user_roles():
    """Post-login scope resolution reads user_roles, not the JWT or the client."""
    from app.services.authorization import INSTITUTION, resolve_authorization_context

    rows = [
        {
            "role_id": uuid4(),
            "role_name": "staff",
            "is_active": True,
            "scope_type": INSTITUTION,
            "scope_id": str(INSTITUTION_A),
            "scope_organization_id": str(ORGANIZATION_ID),
        }
    ]
    user = {"user_id": uuid4(), "email": STAFF_EMAIL, "institution_id": str(INSTITUTION_A)}
    with patch(
        "app.services.authorization.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.repositories.tenancy.get_user_role_scope_rows", return_value=rows
    ), patch(
        "app.repositories.tenancy.get_institution_organization",
        return_value=ORGANIZATION_ID,
    ):
        context = resolve_authorization_context(user)

    assert context["scope_type"] == INSTITUTION
    assert context["institution_id"] == str(INSTITUTION_A)
    assert context["roles"] == ["staff"]


def test_20d_legacy_unscoped_tenant_row_is_not_widened_to_platform():
    """A pre-6.13 tenant-bound role row keeps institution scope (no escalation)."""
    from app.services.authorization import INSTITUTION, resolve_authorization_context

    rows = [
        {
            "role_id": uuid4(),
            "role_name": "staff",
            "is_active": True,
            "scope_type": None,
            "scope_id": None,
            "scope_organization_id": None,
        }
    ]
    user = {"user_id": uuid4(), "email": STAFF_EMAIL, "institution_id": str(INSTITUTION_A)}
    with patch(
        "app.services.authorization.get_admin_client", return_value=MagicMock()
    ), patch(
        "app.repositories.tenancy.get_user_role_scope_rows", return_value=rows
    ), patch(
        "app.repositories.tenancy.get_institution_organization",
        return_value=ORGANIZATION_ID,
    ):
        context = resolve_authorization_context(user)

    assert context["scope_type"] == INSTITUTION
    assert context["scope_id"] == str(INSTITUTION_A)
# ===========================================================================
# 21. Invalid login input (fail-closed at the existing validation boundary)
# ===========================================================================


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"identifier": "", "password": ACCOUNT_PASSWORD},
        {"identifier": "   ", "password": ACCOUNT_PASSWORD},
        {"identifier": APPROVED_EMAIL},
        {"identifier": APPROVED_EMAIL, "password": ""},
        {"password": ACCOUNT_PASSWORD},
    ],
)
def test_21a_student_login_invalid_input_rejected(payload):
    response = client.post(STUDENT_LOGIN_URL, json=payload)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("identifier", [APPROVED_REGISTER, APPROVED_ROLL])
def test_21b_academic_identifier_requires_institution_code(identifier):
    """Register/roll number login without institution_code is invalid input."""
    response = client.post(
        STUDENT_LOGIN_URL, json={"identifier": identifier, "password": ACCOUNT_PASSWORD}
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "institution_code" in body["error"]["message"]


@pytest.mark.parametrize("blank", ["", "   "])
def test_21c_blank_institution_code_rejected(blank):
    response = client.post(
        STUDENT_LOGIN_URL,
        json={
            "identifier": APPROVED_REGISTER,
            "password": ACCOUNT_PASSWORD,
            "institution_code": blank,
        },
    )
    assert response.status_code == 422, response.text


def test_21d_unknown_institution_code_denied_generically():
    """An unknown institution code yields the generic credentials failure."""
    response = student_login_api(
        student=None,
        identifier=APPROVED_REGISTER,
        institution_code="NOPE",
        institution=None,
        by_register=None,
        by_roll=None,
        by_email=None,
    )
    assert_student_failure(response)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": APPROVED_EMAIL},
        {"password": ACCOUNT_PASSWORD},
        {"email": "not-an-email", "password": ACCOUNT_PASSWORD},
        {"email": APPROVED_EMAIL, "password": "short"},
    ],
)
def test_21e_email_login_invalid_input_rejected(payload):
    response = client.post(LOGIN_URL, json=payload)
    assert response.status_code == 422, response.text


def test_21f_malformed_json_body_rejected():
    response = client.post(
        STUDENT_LOGIN_URL,
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422, response.text
# ===========================================================================
# 22-23. Password security — never returned / never logged / never stored
# ===========================================================================

SECRET_PASSWORD = "Sup3rSecret-Login-Pass!"


def test_22a_password_never_returned_on_student_login_success():
    response = student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
    )
    assert response.status_code == 200, response.text
    _assert_no_secret(response, SECRET_PASSWORD)


def test_22b_password_never_returned_on_email_login_success():
    response = login_api(account=student_account(), password=SECRET_PASSWORD)
    assert response.status_code == 200, response.text
    _assert_no_secret(response, SECRET_PASSWORD)


def test_22c_password_never_returned_on_failure():
    """Failures never echo the submitted password (student + email)."""
    student_fail = student_login_api(
        student=student_row(),
        identifier=APPROVED_EMAIL,
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    assert student_fail.status_code == 401
    _assert_no_secret(student_fail, SECRET_PASSWORD)

    email_fail = login_api(
        account=student_account(),
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    assert email_fail.status_code == 400
    _assert_no_secret(email_fail, SECRET_PASSWORD)


def test_22d_no_password_field_in_any_login_payload():
    """No ``password`` key is ever present in a login response body."""
    for response in (
        login_api(account=student_account()),
        student_login_api(
            student=student_row(),
            identifier=APPROVED_REGISTER,
            institution_code=INSTITUTION_CODE,
        ),
    ):
        body = response.json()
        assert "password" not in body
        assert "password" not in body.get("user", {})
        assert "password" not in json.dumps(body).lower().replace(
            '"invalid identifier or password"', ""
        )


def _assert_no_secret(response, secret: str) -> None:
    assert secret not in response.text
    body = response.json()
    assert secret not in json.dumps(body)
    for value in body.values():
        assert value != secret
    if isinstance(body.get("user"), dict):
        for value in body["user"].values():
            assert value != secret
def test_23a_password_never_logged(caplog):
    """No code path logs the submitted password (success, wrong password,
    pending account, and academic identifier login included)."""
    caplog.set_level(logging.DEBUG)

    login_api(account=student_account(), password=SECRET_PASSWORD)
    login_api(
        account=student_account(),
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )
    login_api(account=student_account(approval_status="pending"), password=SECRET_PASSWORD)
    student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
    )
    student_login_api(
        student=student_row(),
        identifier=APPROVED_EMAIL,
        password=SECRET_PASSWORD,
        auth=auth_client(success=False),
    )

    assert SECRET_PASSWORD not in caplog.text
    assert ACCOUNT_PASSWORD not in caplog.text


def test_23b_password_never_written_to_database():
    """The password is only ever handed to Supabase Auth, never to a DB call.

    Every PostgREST call made during a successful student login is inspected:
    no insert/update/eq/select payload may contain the password.
    """
    db = institution_db()
    response = student_login_api(
        student=student_row(),
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        password=SECRET_PASSWORD,
        db=db,
    )
    assert response.status_code == 200, response.text

    for call in db.method_calls:
        assert SECRET_PASSWORD not in repr(call), call


def test_23c_password_never_persisted_by_the_service_layer():
    """The service layer never writes a password column and never sends it to
    the identity repositories — only the identifier is looked up."""
    student = student_row()
    with patch(
        "app.services.student_auth.get_admin_client", return_value=institution_db()
    ), patch(
        "app.services.student_auth.create_supabase_client",
        return_value=auth_client(student),
    ), patch(
        "app.repositories.admin_academics.get_student_by_register_number",
        return_value=student,
    ) as lookup, patch(
        "app.repositories.admin_academics.get_student_by_university_roll_number",
        return_value=None,
    ):
        from app.services.student_auth import authenticate_student

        authenticate_student(APPROVED_REGISTER, SECRET_PASSWORD, INSTITUTION_CODE)

    lookup_args = repr(lookup.call_args)
    assert SECRET_PASSWORD not in lookup_args
    assert APPROVED_REGISTER in lookup_args


def test_23d_password_forwarded_only_to_supabase_auth():
    """The password is handed to GoTrue exactly once and nowhere else."""
    student = student_row()
    auth = auth_client(student)
    with patch(
        "app.services.student_auth.get_admin_client", return_value=institution_db()
    ), patch(
        "app.services.student_auth.create_supabase_client", return_value=auth
    ), patch(
        "app.repositories.admin_academics.get_student_by_email_global",
        return_value=student,
    ):
        from app.services.student_auth import authenticate_student

        authenticate_student(APPROVED_EMAIL, SECRET_PASSWORD)

    auth.auth.sign_in_with_password.assert_called_once_with(
        {"email": APPROVED_EMAIL, "password": SECRET_PASSWORD}
    )


def test_23e_login_schemas_carry_no_password_storage_field():
    """No response schema anywhere exposes a stored/plaintext password field."""
    from app.schemas.student_auth import StudentLoginRequest, StudentLoginResponse
    from app.schemas.users import UserRegistrationResponse

    assert set(StudentLoginRequest.model_fields) == {
        "identifier",
        "password",
        "institution_code",
    }
    assert set(StudentLoginResponse.model_fields) == {"access_token", "message", "user"}
    assert "password" not in set(UserRegistrationResponse.model_fields)

# ===========================================================================
# 24. Existing Phase 6 login regression (nothing locked was changed)
# ===========================================================================


def test_24a_phase_6_email_login_response_shape_unchanged():
    response = login_api(account=student_account())
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"access_token", "message", "user"}
    assert body["message"] == "Login successful."
    assert set(body["user"]) == {"id", "email"}


def test_24b_phase_6_email_login_wrong_password_contract_unchanged():
    response = login_api(account=student_account(), auth=auth_client(success=False))
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid login credentials"


def test_24c_phase_6_5_student_login_failure_contract_unchanged():
    response = student_login_api(
        student=student_row(), identifier=APPROVED_EMAIL, auth=auth_client(success=False)
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid identifier or password"


def test_24d_phase_6_5_student_login_success_contract_unchanged():
    for identifier, extra in (
        (APPROVED_EMAIL, {}),
        (APPROVED_REGISTER, {"institution_code": INSTITUTION_CODE}),
        (APPROVED_ROLL, {"institution_code": INSTITUTION_CODE}),
    ):
        response = student_login_api(
            student=student_row(), identifier=identifier, **extra
        )
        assert response.status_code == 200, f"{identifier}: {response.text}"
        body = response.json()
        assert set(body) == {"access_token", "message", "user"}
        assert body["access_token"] == "mock-access-token"
        assert set(body["user"]) == {"id", "email"}


def test_24e_safe_auth_failure_shape_unchanged():
    exc = SafeAuthFailure()
    assert exc.status_code == 401
    assert exc.code == "INVALID_CREDENTIALS"
    assert exc.message == "Invalid identifier or password"


def test_24f_get_current_user_contract_unchanged():
    """No credentials -> 401 AUTH_REQUIRED (existing dependency untouched)."""
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    bad_scheme = client.get(
        "/api/v1/admin/me", headers={"Authorization": "Basic abc"}
    )
    assert bad_scheme.status_code == 401
    assert bad_scheme.json()["error"]["code"] == "INVALID_SCHEME"


def test_24g_get_current_user_still_requires_an_application_user():
    """A valid JWT with no public.users row -> 404 USER_NOT_FOUND (unchanged)."""
    with patch("app.core.security.verify_jwt", return_value=FAKE_CLAIMS), patch(
        "app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=None)
    ):
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_24h_get_current_user_projections_still_drive_rbac():
    """roles + institution_id still come from get_user_by_auth_id."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": ADMIN_EMAIL}
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 200, response.text
    assert response.json()["roles"] == ["admin"]
    assert response.json()["is_admin"] is True
# ===========================================================================
# 25. Phase 6.13.1-6.13.5 regression (cross-phase invariants still hold)
# ===========================================================================


def test_25a_phase_6_13_1_hierarchy_guard_unchanged():
    """organization <-> institution consistency is still enforced server-side."""
    from app.services.authorization import assert_institution_in_organization

    # Same organization -> allowed.
    assert_institution_in_organization(ORGANIZATION_ID, ORGANIZATION_ID)

    # Cross-organization -> ORGANIZATION_MISMATCH (defense in depth).
    with pytest.raises(AppError) as exc:
        assert_institution_in_organization(ORGANIZATION_ID, uuid4())
    assert exc.value.status_code == 403
    assert exc.value.code == "ORGANIZATION_MISMATCH"

    # Missing side -> denied (never silently allowed).
    with pytest.raises(AppError):
        assert_institution_in_organization(None, ORGANIZATION_ID)


def test_25b_phase_6_13_3_scope_accessors_unchanged():
    """Organization/institution ids are extracted from the resolved context."""
    from app.services.authorization import user_institution_id, user_organization_id

    context = {
        "organization_id": str(ORGANIZATION_ID),
        "institution_id": str(INSTITUTION_A),
    }
    assert user_organization_id(context) == ORGANIZATION_ID
    assert user_institution_id(context) == INSTITUTION_A
    assert user_organization_id({}) is None
    assert user_institution_id({"institution_id": None}) is None


def test_25c_phase_6_13_5_registration_gate_semantics_unchanged():
    """Registration still denies non-ACTIVE institutions (Phase 6.13.5 gate).

    The sign-in gate (Phase 6.13.6) reuses the SAME status semantics: a
    non-active institution carries ``is_active = False`` (trigger-derived), so
    both boundaries deny — registration with 403
    INSTITUTION_NOT_ACCEPTING_REGISTRATIONS, sign-in with 401
    INVALID_CREDENTIALS (anti-enumeration).
    """
    from app.services.tenancy import _assert_institution_active as registration_gate

    registration_gate({"status": "active", "is_active": True})  # allowed

    for status in ("pending", "rejected", "inactive"):
        with pytest.raises(AppError) as exc:
            registration_gate({"status": status, "is_active": False})
        assert exc.value.status_code == 403
        assert exc.value.code == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"

    # The sign-in gate reuses the Phase 6.5 checker on the same rows.
    from app.services.student_auth import _assert_institution_active as sign_in_gate

    with pytest.raises(SafeAuthFailure):
        sign_in_gate(institution_db(is_active=False), INSTITUTION_A)


def test_25d_phase_6_13_5_role_map_unchanged_no_new_roles():
    """Self-registration still grants only student/faculty/staff — no new
    roles were invented by Phase 6.13.6."""
    from app.services.user_registration import ROLE_MAP

    assert ROLE_MAP == {"student": "student", "faculty": "faculty", "staff": "staff"}
    assert "admin" not in ROLE_MAP.values()


def test_25e_phase_6_13_6_single_status_seam():
    """No duplicate status logic: the sign-in guard reuses the Phase 6.5
    institution checker and defines only the 'active' literal it needs."""
    import app.services.sign_in as sign_in

    assert sign_in.ACTIVE == "active"
    assert sign_in._assert_institution_active is (
        __import__(
            "app.services.student_auth", fromlist=["_assert_institution_active"]
        )._assert_institution_active
    )


def test_25f_phase_6_13_5_student_login_still_requires_registered_identity():
    """A registration created in Phase 6.13.5 (pending) cannot log in until
    approved — the two phases agree on the same server-side records."""
    pending = sign_in_account(
        institution_id=str(INSTITUTION_A),
        approval_status="pending",
        student_is_active=True,
    )
    assert_login_failure(login_api(account=pending))

    # A students row missing entirely (faculty/staff) still uses email login.
    staff = sign_in_account()
    response = login_api(account=staff, email=STAFF_EMAIL)
    assert response.status_code == 200, response.text
