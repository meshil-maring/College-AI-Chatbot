"""Authentication password change endpoints."""

import logging

from fastapi import Depends, Header, Request
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.core.security import get_current_user
from app.api.auth import common
from app.schemas.auth.auth import PasswordChangeRequest


logger = logging.getLogger(__name__)


router = common.create_feature_router()


@router.post("/change-password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Verify the current credential, update the password, and revoke other sessions."""
    common.enforce_auth_rate_limit("password", request)
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
        verified = common.create_supabase_client().auth.sign_in_with_password(
            {"email": email, "password": body.current_password}
        )
    except AuthApiError as exc:
        common.record_auth_security_event(
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
        common.get_admin_client().auth.admin.update_user_by_id(
            str(current_user["auth_user_id"]),
            {"password": body.new_password},
        )
        common.create_supabase_client().auth.admin.sign_out(
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

    common.record_auth_security_event(
        event="password_change",
        status="success",
        request=request,
        user_id=str(current_user["user_id"]),
        auth_user_id=str(current_user["auth_user_id"]),
    )
    return {
        "message": "Password changed successfully. Other sessions were signed out."
    }
