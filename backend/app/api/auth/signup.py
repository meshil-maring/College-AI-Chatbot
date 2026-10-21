"""Authentication signup endpoints."""

import logging

from fastapi import Request
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.api.auth import common
from app.schemas.auth.auth import AuthRequest, PASSWORD_MIN_LENGTH


logger = logging.getLogger(__name__)


router = common.create_feature_router()


@router.post("/signup", status_code=201)
def signup(body: AuthRequest, request: Request):
    common.enforce_auth_rate_limit("registration", request)
    if len(body.password) < PASSWORD_MIN_LENGTH:
        raise AppError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters.",
            status_code=422,
            code="VALIDATION_ERROR",
        )
    try:
        client = common.create_supabase_client()
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
    except AuthApiError as exc:
        logger.warning("event=auth_signup_failed category=%s", type(exc).__name__)
        raise AppError(
            "Signup could not be completed. Check the submitted details and try again.",
            status_code=400,
            code="AUTH_SIGNUP_FAILED",
        ) from exc
