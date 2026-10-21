"""Authentication sessions endpoints."""

import logging

from fastapi import Depends, Header, Request
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.core.security import get_current_user
from app.services.auth.sign_in import assert_sign_in_allowed
from app.services.auth.student_auth import SafeAuthFailure
from app.api.auth import common
from app.schemas.auth.auth import RefreshRequest


logger = logging.getLogger(__name__)


router = common.create_feature_router()


@router.post("/refresh")
async def refresh_session(body: RefreshRequest, request: Request) -> dict:
    """Renew the existing Supabase session using its provider refresh token."""
    common.enforce_auth_rate_limit("login", request)
    try:
        response = common.create_supabase_client().auth.refresh_session(body.refresh_token)
    except AuthApiError as exc:
        common.record_auth_security_event(
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

    account = await common.get_sign_in_context(str(response.user.id))
    try:
        assert_sign_in_allowed(common.get_admin_client(), account)
    except SafeAuthFailure as exc:
        # The provider has verified this existing session. Preserve the same
        # inactive-account convention as /auth/me without exposing status on
        # password login or changing the approval/institution guards above.
        if account is not None and (
            account.get("status") in {"inactive", "deactivated"}
            or account.get("student_is_active") is False
        ):
            raise AppError(
                "This account is not active",
                status_code=403,
                code="ACCOUNT_INACTIVE",
            ) from exc
        raise AppError(
            "The session could not be renewed. Please sign in again.",
            status_code=401,
            code="SESSION_REFRESH_FAILED",
        ) from exc

    common.record_auth_security_event(
        event="session_refresh",
        status="success",
        request=request,
        user_id=str(account["user_id"]),
        auth_user_id=str(response.user.id),
    )
    return common.session_payload(response.session, response.user)


def _revoke_session(
    scope: str,
    request: Request,
    authorization: str,
    current_user: dict,
) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    try:
        common.create_supabase_client().auth.admin.sign_out(token, scope=scope)
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
    common.record_auth_security_event(
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
