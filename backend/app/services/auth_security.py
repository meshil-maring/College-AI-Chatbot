"""Rate limiting and audit events for authentication security operations."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import Request

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.services.public_abuse_controls import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

_RATE_LIMITED_MESSAGE = "Too many authentication requests. Please try again later."
_rate_limiter = SlidingWindowRateLimiter()


def enforce_auth_rate_limit(
    operation: str,
    request: Request,
) -> None:
    """Apply an operation-specific budget to the direct peer address."""
    if not settings.auth_rate_limit_enabled:
        return

    peer = request.client.host if request.client is not None else "unknown"
    registration_limit = settings.auth_registration_ip_limit_requests
    if settings.is_local_environment:
        # Development/test clients commonly share one loopback peer. Keep the
        # production default strict without coupling unrelated local tests.
        registration_limit = max(registration_limit, 10_000)
    limits = {
        "login": settings.auth_login_ip_limit_requests,
        "registration": registration_limit,
        "recovery": settings.auth_recovery_ip_limit_requests,
        "password": settings.auth_password_ip_limit_requests,
    }
    if operation not in limits:
        raise ValueError(f"Unsupported authentication rate-limit operation: {operation}")

    retry_after = _rate_limiter.check(
        [("auth-" + operation, peer or "unknown", limits[operation])],
        settings.auth_rate_limit_window_seconds,
    )
    if retry_after is None:
        return

    logger.warning("event=auth_rate_limited operation=%s status=429", operation)
    raise AppError(
        _RATE_LIMITED_MESSAGE,
        status_code=429,
        code="AUTH_RATE_LIMITED",
        headers={"Retry-After": str(retry_after)},
    )


def record_auth_security_event(
    *,
    event: str,
    status: str,
    request: Request,
    user_id: str | None = None,
    auth_user_id: str | None = None,
) -> None:
    """Persist a security event without passwords, tokens, or identifiers from input."""
    peer = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent", "")[:512] or None
    row = {
        "user_id": user_id,
        "auth_user_id": auth_user_id,
        "event": event,
        "status": status,
        "ip_address": peer,
        "user_agent": user_agent,
    }
    try:
        get_admin_client().table("auth_security_events").insert(row).execute()
    except Exception as exc:
        logger.error(
            "event=auth_security_audit_failed action=%s category=%s",
            event,
            type(exc).__name__,
        )
        raise AppError(
            "Authentication security event could not be recorded.",
            status_code=503,
            code="AUTH_AUDIT_UNAVAILABLE",
        ) from exc


def consume_password_recovery_session(
    *,
    session_id: str,
    auth_user_id: str,
    expires_at: int,
) -> bool:
    """Atomically mark a verified provider recovery session as single-use."""
    fingerprint = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    try:
        response = get_admin_client().rpc(
            "consume_auth_password_recovery_session",
            {
                "p_session_fingerprint": fingerprint,
                "p_auth_user_id": auth_user_id,
                "p_expires_at": datetime.fromtimestamp(
                    expires_at,
                    tz=timezone.utc,
                ).isoformat(),
            },
        ).execute()
    except Exception as exc:
        logger.error(
            "event=auth_recovery_session_consume_failed category=%s",
            type(exc).__name__,
        )
        raise AppError(
            "Password recovery is temporarily unavailable. Please try again later.",
            status_code=503,
            code="AUTH_RECOVERY_UNAVAILABLE",
        ) from exc

    if isinstance(response.data, bool):
        return response.data
    logger.error("event=auth_recovery_session_consume_failed category=invalid_response")
    raise AppError(
        "Password recovery is temporarily unavailable. Please try again later.",
        status_code=503,
        code="AUTH_RECOVERY_UNAVAILABLE",
    )


def reset_auth_abuse_state() -> None:
    """Clear process-local counters for deterministic tests."""
    _rate_limiter.reset()
