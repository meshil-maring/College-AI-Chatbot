"""DEVELOPMENT / TESTING ONLY — password recovery convenience endpoints.

WARNING: Every endpoint in this module is gated by ``settings.dev_test_mode``
and returns 404 ("NOT_FOUND") when that flag is not explicitly enabled
(``DEV_TEST_MODE=true`` in the backend environment). This is NOT part of the
final demo lock and MUST remain disabled outside local development/testing.

Design notes:
  * No custom password storage, hashing, or password table is introduced.
    Every password change goes through the existing Supabase Auth service
    (either the service-role admin API or the normal sign-in-with-password
    flow), exactly like ``app/api/auth.py`` and ``app/core/security.py``.
  * The Supabase service-role ("secret") key never leaves the backend; the
    frontend only ever calls these HTTP endpoints.
  * Passwords, tokens, and other secrets are never logged. Error messages
    surfaced to the client are Supabase's own safe messages or generic
    fallbacks — never a rendered secret.
  * Existing JWT/role authentication is not modified or bypassed for any
    other endpoint. The admin-reset endpoint below still requires the
    existing ``require_roles("admin")`` dependency in addition to the dev
    flag.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, field_validator
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.errors import AppError
from app.core.security import require_roles
from app.db.supabase import create_supabase_client, get_admin_client

router = APIRouter(prefix="/dev/auth", tags=["dev-auth (DEV/TEST ONLY)"])


def _require_dev_test_mode() -> None:
    """Hard boundary: every handler in this module calls this first.

    Returns 404 (rather than 403) so the feature's existence is not
    disclosed when disabled outside development/testing.
    """
    if not settings.dev_test_mode:
        raise AppError(
            "Not found",
            status_code=404,
            code="NOT_FOUND",
        )


def _validate_password(v: str) -> str:
    """Mirror the existing signup/login password rule (app/api/auth.py)."""
    if len(v) < 6:
        raise ValueError("Password must be at least 6 characters")
    return v


class DevPasswordResetRequest(BaseModel):
    """DEV/TEST ONLY — reset a password by email, without OTP/email verification."""

    email: EmailStr
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _password_min_length(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def _confirm_matches(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and v != new_password:
            raise ValueError("Passwords do not match")
        return v


class DevChangePasswordRequest(BaseModel):
    """DEV/TEST ONLY — change password for the currently authenticated user."""

    email: EmailStr
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _password_min_length(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def _confirm_matches(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and v != new_password:
            raise ValueError("Passwords do not match")
        return v


class DevAdminResetRequest(BaseModel):
    """DEV/TEST ONLY — admin-triggered reset of a student's password."""

    email: EmailStr
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def _password_min_length(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("confirm_password")
    @classmethod
    def _confirm_matches(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and v != new_password:
            raise ValueError("Passwords do not match")
        return v


def _find_auth_user_id_by_email(email: str) -> str | None:
    """Look up a Supabase Auth user id by email using the admin API.

    Uses the existing service-role client (app/db/supabase.get_admin_client);
    no custom user table or password storage is introduced.
    """
    admin_client = get_admin_client()
    page = 1
    per_page = 200
    while True:
        users = admin_client.auth.admin.list_users(page=page, per_page=per_page)
        if not users:
            return None
        for user in users:
            if (user.email or "").lower() == email.lower():
                return user.id
        if len(users) < per_page:
            return None
        page += 1


def _update_password_by_auth_user_id(auth_user_id: str, new_password: str) -> None:
    admin_client = get_admin_client()
    admin_client.auth.admin.update_user_by_id(
        auth_user_id, {"password": new_password}
    )


@router.post("/forgot-password")
def dev_forgot_password(body: DevPasswordResetRequest) -> dict:
    """DEV/TEST ONLY. Reset a user's password by email — no OTP/email step.

    Uses Supabase Auth's admin password-management API
    (auth.admin.update_user_by_id) rather than any custom password storage.
    """
    _require_dev_test_mode()
    try:
        auth_user_id = _find_auth_user_id_by_email(body.email)
        if auth_user_id is None:
            raise AppError(
                "No account found for that email.",
                status_code=404,
                code="USER_NOT_FOUND",
            )
        _update_password_by_auth_user_id(auth_user_id, body.new_password)
        return {"message": "Password reset successfully. (DEV/TEST ONLY)"}
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status or 400, code="AUTH_ERROR")


@router.post("/change-password")
def dev_change_password(body: DevChangePasswordRequest) -> dict:
    """DEV/TEST ONLY. Change password for a user who proves current credentials.

    Verifies the current password via the normal Supabase
    sign-in-with-password flow, then updates the password through the
    service-role admin API. No custom authentication logic is added.
    """
    _require_dev_test_mode()
    try:
        client = create_supabase_client()
        client.auth.sign_in_with_password(
            {"email": body.email, "password": body.current_password}
        )
    except AuthApiError:
        raise AppError(
            "Current password is incorrect.",
            status_code=400,
            code="INVALID_CREDENTIALS",
        )

    try:
        auth_user_id = _find_auth_user_id_by_email(body.email)
        if auth_user_id is None:
            raise AppError(
                "No account found for that email.",
                status_code=404,
                code="USER_NOT_FOUND",
            )
        _update_password_by_auth_user_id(auth_user_id, body.new_password)
        return {"message": "Password changed successfully. (DEV/TEST ONLY)"}
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status or 400, code="AUTH_ERROR")


@router.post("/admin/reset-student-password")
def dev_admin_reset_student_password(
    body: DevAdminResetRequest,
    current_user: dict = Depends(require_roles("admin")),
) -> dict:
    """DEV/TEST ONLY. Admin-triggered reset of a student's password.

    Requires the existing ``require_roles("admin")`` authorization in
    addition to the dev/test flag — this does not weaken or bypass the
    production admin authorization mechanism.
    """
    _require_dev_test_mode()
    try:
        auth_user_id = _find_auth_user_id_by_email(body.email)
        if auth_user_id is None:
            raise AppError(
                "No account found for that email.",
                status_code=404,
                code="USER_NOT_FOUND",
            )
        _update_password_by_auth_user_id(auth_user_id, body.new_password)
        return {"message": "Student password reset successfully. (DEV/TEST ONLY)"}
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status or 400, code="AUTH_ERROR")
