"""Authorization scope types and fail-closed errors."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import AppError

PLATFORM = "platform"
ORGANIZATION = "organization"
INSTITUTION = "institution"
ACTIVE_STATUS = "active"
PENDING_STATUS = "pending"


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Minimal, server-owned context for one institution operation."""

    user_id: UUID
    role: str
    scope_type: str
    institution_id: UUID
    is_active: bool


def user_organization_id(authorization_context: dict[str, Any]) -> UUID | None:
    """Return the user's organization id from their resolved context, or None."""
    raw = authorization_context.get("organization_id")
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def user_institution_id(authorization_context: dict[str, Any]) -> UUID | None:
    """Return the user's institution id from their resolved context, or None."""
    raw = authorization_context.get("institution_id")
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _org_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different organization",
        status_code=403,
        code="ORGANIZATION_MISMATCH",
    )


def _scope_forbidden() -> AppError:
    return AppError(
        "You do not have permission to perform this action",
        status_code=403,
        code="FORBIDDEN",
    )


def _tenant_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different institution",
        status_code=403,
        code="TENANT_MISMATCH",
    )


def _scope_missing() -> AppError:
    return AppError(
        "No authorization scope could be resolved for this account",
        status_code=403,
        code="SCOPE_MISSING",
    )


def _scope_inconsistent() -> AppError:
    return AppError(
        "Authorization context is inconsistent or incomplete",
        status_code=403,
        code="SCOPE_INCONSISTENT",
    )


def _tenant_inactive() -> AppError:
    return AppError(
        "This institution is not active",
        status_code=403,
        code="TENANT_INACTIVE",
    )


def _organization_inactive() -> AppError:
    return AppError(
        "This organization is not active",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
    )
