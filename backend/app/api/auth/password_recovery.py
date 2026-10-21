"""Authentication password recovery endpoints."""

import logging
import time

from fastapi import Depends, Header, Request
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.errors import AppError
from app.core.security import get_current_user
from app.api.auth import common
from app.schemas.auth.auth import PasswordRecoveryRequest, PasswordResetCompletionRequest


logger = logging.getLogger(__name__)

PASSWORD_RECOVERY_MAX_AGE_SECONDS = 900

RECOVERY_SUBMITTED_MESSAGE = (
    "If an account exists, password recovery instructions have been sent."
)


router = common.create_feature_router()


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


@router.post("/forgot-password")
def forgot_password(body: PasswordRecoveryRequest, request: Request) -> dict:
    """Ask Supabase Auth to send its single-use recovery email."""
    common.enforce_auth_rate_limit("recovery", request)
    try:
        redirect_to = settings.effective_auth_recovery_redirect_url
        common.create_supabase_client().auth.reset_password_for_email(
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

    common.record_auth_security_event(
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
    common.enforce_auth_rate_limit("password", request)
    recovery_timestamp = _recent_password_recovery_timestamp(current_user)
    if recovery_timestamp is None:
        common.record_auth_security_event(
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
    if not common.consume_password_recovery_session(
        session_id=recovery_session_id,
        auth_user_id=str(current_user["auth_user_id"]),
        expires_at=recovery_timestamp + PASSWORD_RECOVERY_MAX_AGE_SECONDS,
    ):
        common.record_auth_security_event(
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
        common.get_admin_client().auth.admin.update_user_by_id(
            str(current_user["auth_user_id"]),
            {"password": body.new_password},
        )
        # Supabase revokes refresh sessions globally. Existing JWT access
        # tokens remain valid only until their provider-defined expiry.
        common.create_supabase_client().auth.admin.sign_out(
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

    common.record_auth_security_event(
        event="password_reset",
        status="success",
        request=request,
        user_id=str(current_user["user_id"]),
        auth_user_id=str(current_user["auth_user_id"]),
    )
    return {"message": "Password reset successfully. Please sign in again."}
