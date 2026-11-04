"""Shared token and database error handling for student onboarding."""

import hashlib
import secrets
from typing import Any, Callable

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.services.academics.database_errors import translate_database_error

INVALID_LINK = AppError("This student setup link is invalid or expired.", 400, "INVITATION_INVALID")


def token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("ascii")).hexdigest()


def database(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except AppError:
        raise
    except APIError as exc:
        code = getattr(exc, "code", None)
        if code in {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}:
            raise AppError(
                "Student registration setup is unavailable. Ask your administrator "
                "to apply the student onboarding migration and refresh the database schema cache.",
                503,
                "STUDENT_ONBOARDING_SCHEMA_UNAVAILABLE",
            ) from exc
        if code == "23505":
            raise AppError("Email, Register Number, or University Roll No. is already in use.", 409, "STUDENT_IDENTITY_EXISTS") from exc
        if code == "P0001":
            raise AppError("The invitation resend limit has been reached. Try again later.", 429, "RESEND_LIMIT") from exc
        if code == "P0003":
            raise AppError(
                "Setup has already started for this invitation. It cannot be cancelled.",
                409,
                "INVITATION_SETUP_STARTED",
            ) from exc
        if code == "P0004":
            raise AppError(
                "Setup has already started for this invitation. Its email cannot be changed.",
                409,
                "INVITATION_EMAIL_LOCKED",
            ) from exc
        if code == "P0002":
            raise INVALID_LINK from exc
        if code == "P1002":
            raise AppError("The selected section is full. Ask your administrator to assign an available section.", 409, "SECTION_CAPACITY") from exc
        if code == "23514":
            raise AppError("The academic section is no longer available. Ask your administrator to assign an active section.", 409, "SECTION_INACTIVE") from exc
        if code == "42501":
            message = str(getattr(exc, "message", "") or "").lower()
            if "permission denied for table" in message:
                raise AppError(
                    "Student setup is temporarily unavailable because the onboarding database permissions are incomplete. "
                    "Ask your administrator to apply the latest student onboarding migration.",
                    503,
                    "STUDENT_ONBOARDING_PERMISSION_UNAVAILABLE",
                ) from exc
            raise AppError(
                "Student setup requires administrator review. Contact your institution administrator.",
                403,
                "STUDENT_SETUP_REVIEW_REQUIRED",
            ) from exc
        raise translate_database_error(exc) from exc
