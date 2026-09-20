"""DEVELOPMENT / TESTING ONLY — password recovery convenience endpoints.

WARNING: Every endpoint in this module is gated by ``settings.dev_test_mode``
and returns 404 ("NOT_FOUND") when that flag is not explicitly enabled
(``DEV_TEST_MODE=true`` in the backend environment). This is NOT part of the
final demo lock and MUST remain disabled outside local development/testing.

Phase 6.15.7 hardening:
  * The gate is applied at ROUTER level (``dependencies=[Depends(...)]``) in
    addition to the per-handler check, so a disabled deployment answers 404
    BEFORE the request body is parsed/validated — a malformed or unexpected
    payload can never turn a hidden route into a 422 disclosure.
  * Every request schema uses ``extra="forbid"``: unexpected fields (for
    example a client-supplied ``role``, ``user_id`` or ``password`` alias) are
    rejected with 422 instead of being silently ignored.
  * ``app/config.py`` refuses to start when ``DEV_TEST_MODE`` is enabled
    outside a local development/testing ``ENVIRONMENT``, so this module can
    never be switched on in a deployed environment by misconfiguration.

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
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.errors import AppError
from app.core.security import require_roles
from app.db.supabase import create_supabase_client, get_admin_client


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


router = APIRouter(
    prefix="/dev/auth",
    tags=["dev-auth (DEV/TEST ONLY)"],
    # Phase 6.15.7 — the flag is enforced as a ROUTER dependency so it runs
    # before the request body is validated: a disabled deployment answers 404
    # for every dev route and every payload shape, revealing nothing.
    dependencies=[Depends(_require_dev_test_mode)],
)


def _validate_password(v: str) -> str:
    """Mirror the existing signup/login password rule (app/api/auth.py)."""
    if len(v) < 6:
        raise ValueError("Password must be at least 6 characters")
    return v


# Phase 6.15.6 — anti-enumeration response for the recovery endpoint.
#
# The SAME generic message is returned for a known email and an unknown email
# (with the same HTTP 200 status), so the response body/status can never be
# used to discover whether an account exists. This mirrors the anti-enumeration
# contract already used by ``/auth/login`` and ``/auth/student/login`` (every
# denial is normalized so account existence is never disclosed). Because the
# endpoint performs a direct reset (no email is sent), the message states the
# reset outcome generically instead of promising an email.
_GENERIC_RECOVERY_MESSAGE = (
    "If an account exists for this email, the password has been reset. "
    "You can now sign in with your new password. (DEV/TEST ONLY)"
)


class DevPasswordResetRequest(BaseModel):
    """DEV/TEST ONLY — reset a password by email, without OTP/email verification.

    ``extra="forbid"`` (Phase 6.15.7): the request may contain EXACTLY these
    three fields — a client can never smuggle in ``role``, ``user_id`` or any
    other field that the service might later consider.
    """

    model_config = ConfigDict(extra="forbid")

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
    """DEV/TEST ONLY — change password for the currently authenticated user.

    ``extra="forbid"`` (Phase 6.15.7) — same contract as the other dev-only
    schemas: exactly these four fields.
    """

    model_config = ConfigDict(extra="forbid")

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
    """DEV/TEST ONLY — admin-triggered reset of a student's password.

    ``extra="forbid"`` (Phase 6.15.7) — the admin identity and role are NEVER
    accepted from the payload; they come only from the verified JWT through
    ``require_roles("admin")``.
    """

    model_config = ConfigDict(extra="forbid")

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

    Phase 6.15.6 — anti-enumeration: an unknown email produces the SAME
    generic 200 response as a successful reset (``_GENERIC_RECOVERY_MESSAGE``)
    and no password is changed. The endpoint can therefore never be used to
    discover whether an account exists, matching the locked login contracts.
    Supabase Auth failures still surface as the existing ``AUTH_ERROR``
    envelope (an operational error, not an account-existence signal).
    """
    _require_dev_test_mode()
    try:
        auth_user_id = _find_auth_user_id_by_email(body.email)
        if auth_user_id is not None:
            _update_password_by_auth_user_id(auth_user_id, body.new_password)
        return {"message": _GENERIC_RECOVERY_MESSAGE}
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
