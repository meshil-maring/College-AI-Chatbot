"""Authentication endpoints (Phase 5.4 + Phase 6.13.6).

``POST /auth/signup`` — existing Supabase Auth signup (unchanged).
``POST /auth/login``  — email + password sign-in for every account that uses
the existing email identity model (admins, faculty, staff, and the demo
accounts). Phase 6.13.6 extends this endpoint IN PLACE — no duplicate
endpoint, no second authentication system:

    1. Credentials are verified by Supabase Auth (GoTrue), the SINGLE
       credential authority. The password is never stored, hashed, compared,
       logged, or echoed by this application.
    2. After successful authentication the account is resolved server-side
       through the existing tenant-resolution chain
       (``auth.users -> public.users -> students -> institutions``) via
       ``get_sign_in_context`` (additive sibling of ``get_user_by_auth_id``).
    3. Status guard (fail-closed): sign-in completes only when
           * the ``public.users`` row exists,
           * ``users.status == 'active'``,
           * tenant-bound (students profile) accounts are Phase 6.4 approved,
             lifecycle-active, and their institution is active.
       All denials normalize to the LOCKED Phase 5.4 login failure contract —
       ``400 INVALID_CREDENTIALS`` with the same message Supabase Auth emits
       for a wrong password — so account existence, approval state, and
       lifecycle state are never disclosed (anti-enumeration), and the
       existing frontend mapping (400 + ``INVALID_CREDENTIALS`` ->
       ``invalid_credentials``) keeps working unchanged.

Authorization (role, organization/institution scope) is NEVER accepted from
the client: the request schema uses ``extra="forbid"`` and role/scope are
always resolved from trusted server-side records after authentication.
"""

import logging
import time

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.errors import AppError
from app.core.security import get_current_user
from app.db.supabase import (
    create_supabase_client,
    get_admin_client,
    get_sign_in_context,
)
from app.services.sign_in import assert_sign_in_allowed
from app.services.student_auth import SafeAuthFailure
from app.services.auth_security import (
    consume_password_recovery_session,
    enforce_auth_rate_limit,
    record_auth_security_event,
)
from app.repositories import tenancy as tenancy_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_RECOVERY_MAX_AGE_SECONDS = 900
RECOVERY_SUBMITTED_MESSAGE = (
    "If an account exists, password recovery instructions have been sent."
)


def _pending_registration_for_email(email: str) -> dict | None:
    """Resolve a pending staff/faculty request from a trusted account email."""
    db = get_admin_client()
    user = tenancy_repo.get_user_by_email(db, email)
    if user is None:
        return None
    return tenancy_repo.get_pending_membership_request_for_user(db, user["user_id"])


def _raise_registration_pending(request: dict) -> None:
    role = str(request.get("requested_role") or "faculty")
    raise AppError(
        f"Your {role} registration is pending. Contact your institution administrator to continue.",
        status_code=403,
        code="REGISTRATION_PENDING",
    )


def _recent_password_recovery_timestamp(current_user: dict) -> int | None:
    methods = current_user.get("auth_methods")
    session_id = current_user.get("auth_session_id")
    issued_at = current_user.get("token_issued_at")
    if (
        not isinstance(methods, list)
        or not isinstance(session_id, str)
        or not session_id
        or not isinstance(issued_at, int)
        or isinstance(issued_at, bool)
    ):
        return None

    now = time.time()
    token_age_seconds = now - issued_at
    if not 0 <= token_age_seconds < PASSWORD_RECOVERY_MAX_AGE_SECONDS:
        return None

    for method in methods:
        if not isinstance(method, dict) or method.get("method") != "recovery":
            continue
        recovery_timestamp = method.get("timestamp")
        if (
            not isinstance(recovery_timestamp, (int, float))
            or isinstance(recovery_timestamp, bool)
        ):
            continue
        recovery_age_seconds = now - recovery_timestamp
        if 0 <= recovery_age_seconds < PASSWORD_RECOVERY_MAX_AGE_SECONDS:
            return int(recovery_timestamp)
    return None


class AuthRequest(BaseModel):
    """Login / signup payload.

    ``extra="forbid"`` — clients can NEVER inject ``role``, ``scope_type``,
    ``scope_id``, ``institution_id``, ``organization_id``, ``status``, or any
    other authorization-control field. Role and scope are resolved ONLY from
    trusted server-side records after authentication.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=6, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class PasswordRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    confirm_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("confirm_password")
    @classmethod
    def confirm_matches(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and value != new_password:
            raise ValueError("Passwords do not match")
        return value


class PasswordResetCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    confirm_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("confirm_password")
    @classmethod
    def confirm_matches(cls, value: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and value != new_password:
            raise ValueError("Passwords do not match")
        return value


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


def _session_payload(session, user) -> dict:
    if session is None or not session.access_token or not session.refresh_token:
        raise AppError(
            "The authentication provider did not issue a usable session.",
            status_code=502,
            code="AUTH_SESSION_UNAVAILABLE",
        )
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_in": session.expires_in,
        "message": "Login successful.",
        "user": {"id": user.id, "email": user.email},
    }


@router.post("/signup", status_code=201)
def signup(body: AuthRequest):
    if len(body.password) < PASSWORD_MIN_LENGTH:
        raise AppError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
            status_code=422,
            code="VALIDATION_ERROR",
        )
    try:
        client = create_supabase_client()
        response = client.auth.sign_up({"email": body.email, "password": body.password})
        if response.session is None:
            return {
                "access_token": None,
                "message": "Signup successful. Please check your email to confirm your account.",
                "user": {"id": response.user.id, "email": response.user.email},
            }
        return {
            "access_token": response.session.access_token,
            "message": "Signup successful.",
            "user": {"id": response.user.id, "email": response.user.email},
        }
    except AuthApiError as e:
        raise AppError(e.message, status_code=e.status, code="AUTH_ERROR")


@router.post("/login")
async def login(body: AuthRequest, request: Request):
    """Authenticate with email + password and return a Supabase Auth session.

    Response shape includes the provider access/refresh tokens and
    ``expires_in`` alongside the locked message/user fields.

    The password is forwarded to Supabase Auth only; it is never returned,
    logged, or persisted anywhere. After credential verification the Phase
    6.13.6 status guard decides — server-side — whether the account may
    complete sign-in (public.users row present, ``users.status == 'active'``,
    and tenant-bound accounts approved + active with an active institution).
    """
    enforce_auth_rate_limit("login", request)
    try:
        client = create_supabase_client()
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        # GoTrue may block a newly self-registered account as unconfirmed
        # before issuing a session. This response is only produced after the
        # submitted password has matched, so translating it does not expose a
        # pending account to callers with incorrect credentials.
        auth_code = str(getattr(e, "code", "") or "").lower()
        auth_message = str(getattr(e, "message", "") or "").lower()
        if auth_code == "email_not_confirmed" or "email not confirmed" in auth_message:
            pending = _pending_registration_for_email(str(body.email))
            if pending is not None:
                _raise_registration_pending(pending)
        record_auth_security_event(
            event="login",
            status="failure",
            request=request,
        )
        raise AppError(
            "Invalid login credentials",
            status_code=400,
            code="INVALID_CREDENTIALS",
        ) from e

    # Phase 6.13.6 — post-authentication status guard (fail-closed). The
    # account context is resolved from trusted server-side records only; the
    # client cannot influence user, organization, institution, role, or scope.
    account = await get_sign_in_context(response.user.id)
    # Credentials have already been verified, so it is safe and useful to
    # explain why a self-registered staff/faculty account cannot continue.
    # Incorrect passwords still receive the generic INVALID_CREDENTIALS error
    # above and cannot be used to discover registration state.
    if account is not None:
        pending_request = tenancy_repo.get_pending_membership_request_for_user(
            get_admin_client(), account["user_id"]
        )
        if pending_request is not None:
            _raise_registration_pending(pending_request)
    try:
        assert_sign_in_allowed(get_admin_client(), account)
    except SafeAuthFailure as exc:
        # Normalize every status denial to the LOCKED Phase 5.4 login failure
        # response: 400 INVALID_CREDENTIALS with Supabase's own wording, so the
        # response is byte-for-byte indistinguishable from a wrong password and
        # account existence / approval / lifecycle state is never disclosed.
        record_auth_security_event(
            event="login",
            status="failure",
            request=request,
            user_id=str(account["user_id"]) if account is not None else None,
            auth_user_id=str(response.user.id),
        )
        raise AppError(
            "Invalid login credentials",
            status_code=400,
            code="INVALID_CREDENTIALS",
        ) from exc

    record_auth_security_event(
        event="login",
        status="success",
        request=request,
        user_id=str(account["user_id"]),
        auth_user_id=str(response.user.id),
    )
    return _session_payload(response.session, response.user)


@router.post("/forgot-password")
def forgot_password(body: PasswordRecoveryRequest, request: Request) -> dict:
    """Ask Supabase Auth to send its single-use recovery email."""
    enforce_auth_rate_limit("recovery", request)
    try:
        redirect_to = settings.effective_auth_recovery_redirect_url
        create_supabase_client().auth.reset_password_for_email(
            str(body.email),
            {"redirect_to": redirect_to},
        )
    except (AuthApiError, ValueError) as exc:
        logger.warning(
            "event=auth_recovery_request_failed category=%s",
            type(exc).__name__,
        )
        raise AppError(
            "Password recovery is temporarily unavailable. Please try again later.",
            status_code=503,
            code="AUTH_RECOVERY_UNAVAILABLE",
        ) from exc

    record_auth_security_event(
        event="password_recovery_requested",
        status="info",
        request=request,
    )
    return {"message": RECOVERY_SUBMITTED_MESSAGE}


@router.post("/reset-password")
def complete_password_reset(
    body: PasswordResetCompletionRequest,
    request: Request,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Set a new password using the provider-issued recovery session."""
    enforce_auth_rate_limit("password", request)
    recovery_timestamp = _recent_password_recovery_timestamp(current_user)
    if recovery_timestamp is None:
        record_auth_security_event(
            event="password_reset",
            status="failure",
            request=request,
            user_id=str(current_user["user_id"]),
            auth_user_id=str(current_user["auth_user_id"]),
        )
        raise AppError(
            "The password recovery session is invalid or expired. Request a new link.",
            status_code=400,
            code="PASSWORD_RECOVERY_SESSION_INVALID",
        )

    recovery_session_id = current_user["auth_session_id"]
    if not consume_password_recovery_session(
        session_id=recovery_session_id,
        auth_user_id=str(current_user["auth_user_id"]),
        expires_at=recovery_timestamp + PASSWORD_RECOVERY_MAX_AGE_SECONDS,
    ):
        record_auth_security_event(
            event="password_reset",
            status="failure",
            request=request,
            user_id=str(current_user["user_id"]),
            auth_user_id=str(current_user["auth_user_id"]),
        )
        raise AppError(
            "The password recovery session is invalid or expired. Request a new link.",
            status_code=400,
            code="PASSWORD_RECOVERY_SESSION_INVALID",
        )

    try:
        get_admin_client().auth.admin.update_user_by_id(
            str(current_user["auth_user_id"]),
            {"password": body.new_password},
        )
        # Supabase revokes refresh sessions globally. Existing JWT access
        # tokens remain valid only until their provider-defined expiry.
        create_supabase_client().auth.admin.sign_out(
            authorization.removeprefix("Bearer ").strip(),
            scope="global",
        )
    except AuthApiError as exc:
        logger.warning(
            "event=auth_password_reset_failed category=%s",
            type(exc).__name__,
        )
        raise AppError(
            "Password reset could not be completed. Please request a new link.",
            status_code=503,
            code="PASSWORD_RESET_FAILED",
        ) from exc

    record_auth_security_event(
        event="password_reset",
        status="success",
        request=request,
        user_id=str(current_user["user_id"]),
        auth_user_id=str(current_user["auth_user_id"]),
    )
    return {"message": "Password reset successfully. Please sign in again."}


@router.post("/change-password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Verify the current credential, update the password, and revoke other sessions."""
    enforce_auth_rate_limit("password", request)
    if body.current_password == body.new_password:
        raise AppError(
            "Choose a new password different from your current password.",
            status_code=422,
            code="PASSWORD_UNCHANGED",
        )

    email = current_user.get("email")
    if not isinstance(email, str) or not email:
        raise AppError(
            "Current credentials could not be verified.",
            status_code=400,
            code="PASSWORD_VERIFICATION_FAILED",
        )
    try:
        verified = create_supabase_client().auth.sign_in_with_password(
            {"email": email, "password": body.current_password}
        )
    except AuthApiError as exc:
        record_auth_security_event(
            event="password_change",
            status="failure",
            request=request,
            user_id=str(current_user["user_id"]),
            auth_user_id=str(current_user["auth_user_id"]),
        )
        raise AppError(
            "Current credentials could not be verified.",
            status_code=400,
            code="PASSWORD_VERIFICATION_FAILED",
        ) from exc

    if verified.user is None or str(verified.user.id) != str(current_user["auth_user_id"]):
        raise AppError(
            "Current credentials could not be verified.",
            status_code=400,
            code="PASSWORD_VERIFICATION_FAILED",
        )

    try:
        get_admin_client().auth.admin.update_user_by_id(
            str(current_user["auth_user_id"]),
            {"password": body.new_password},
        )
        create_supabase_client().auth.admin.sign_out(
            authorization.removeprefix("Bearer ").strip(),
            scope="others",
        )
    except AuthApiError as exc:
        logger.warning(
            "event=auth_password_change_failed category=%s",
            type(exc).__name__,
        )
        raise AppError(
            "Password change could not be completed. Please try again later.",
            status_code=503,
            code="PASSWORD_CHANGE_FAILED",
        ) from exc

    record_auth_security_event(
        event="password_change",
        status="success",
        request=request,
        user_id=str(current_user["user_id"]),
        auth_user_id=str(current_user["auth_user_id"]),
    )
    return {
        "message": "Password changed successfully. Other sessions were signed out."
    }


@router.post("/refresh")
async def refresh_session(body: RefreshRequest, request: Request) -> dict:
    """Renew the existing Supabase session using its provider refresh token."""
    enforce_auth_rate_limit("login", request)
    try:
        response = create_supabase_client().auth.refresh_session(body.refresh_token)
    except AuthApiError as exc:
        record_auth_security_event(
            event="session_refresh",
            status="failure",
            request=request,
        )
        raise AppError(
            "The session could not be renewed. Please sign in again.",
            status_code=401,
            code="SESSION_REFRESH_FAILED",
        ) from exc

    if response.session is None or response.user is None:
        raise AppError(
            "The session could not be renewed. Please sign in again.",
            status_code=401,
            code="SESSION_REFRESH_FAILED",
        )

    account = await get_sign_in_context(str(response.user.id))
    try:
        assert_sign_in_allowed(get_admin_client(), account)
    except SafeAuthFailure as exc:
        raise AppError(
            "The session could not be renewed. Please sign in again.",
            status_code=401,
            code="SESSION_REFRESH_FAILED",
        ) from exc

    record_auth_security_event(
        event="session_refresh",
        status="success",
        request=request,
        user_id=str(account["user_id"]),
        auth_user_id=str(response.user.id),
    )
    return _session_payload(response.session, response.user)


def _revoke_session(
    scope: str,
    request: Request,
    authorization: str,
    current_user: dict,
) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    try:
        create_supabase_client().auth.admin.sign_out(token, scope=scope)
    except AuthApiError as exc:
        logger.warning(
            "event=auth_logout_failed scope=%s category=%s",
            scope,
            type(exc).__name__,
        )
        raise AppError(
            "The session could not be revoked by the authentication provider.",
            status_code=503,
            code="SESSION_REVOCATION_FAILED",
        ) from exc
    record_auth_security_event(
        event="logout" if scope == "local" else "logout_all",
        status="success",
        request=request,
        user_id=str(current_user["user_id"]),
        auth_user_id=str(current_user["auth_user_id"]),
    )
    return {"message": "Session revoked."}


@router.post("/logout")
def logout(
    request: Request,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Revoke the current provider session's refresh token."""
    return _revoke_session("local", request, authorization, current_user)


@router.post("/logout-all")
def logout_all(
    request: Request,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Revoke all refresh sessions for the authenticated account."""
    return _revoke_session("global", request, authorization, current_user)
