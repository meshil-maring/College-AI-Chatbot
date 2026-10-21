"""Shared provider dependencies, security hooks and session response helpers."""

from fastapi import APIRouter

from app.core.errors import AppError
from app.db.supabase import create_supabase_client, get_admin_client, get_sign_in_context
from app.services.auth.auth_security import (
    consume_password_recovery_session,
    enforce_auth_rate_limit,
    record_auth_security_event,
)


def session_payload(session, user) -> dict:
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


def create_feature_router() -> APIRouter:
    """Preserve the /auth prefix on each feature route template."""
    return APIRouter(prefix="/auth")
