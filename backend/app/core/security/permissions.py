"""Security permissions responsibilities."""

import logging

from fastapi import Depends

from typing import Callable

from app.core.errors import AppError
from app.core.permissions import fallback_permissions_for_roles, permission_matches
from app.core.security.identity import get_current_user


logger = logging.getLogger(__name__)


def has_permission(current_user: dict, permission: str) -> bool:
    """Check a permission against the resolved server-side grant set.

    The role-matrix fallback exists only for internal/test dependency overrides
    that construct ``current_user`` directly. Real requests always carry
    ``permissions_resolved=True`` from the database projection, so absent or
    revoked database grants never fall back to role defaults.
    """
    if current_user.get("permissions_resolved") is True:
        granted = current_user.get("effective_permissions") or ()
    else:
        granted = fallback_permissions_for_roles(current_user.get("roles") or ())
    return permission_matches(granted, permission)


def _deny_permission(current_user: dict, permission: str) -> AppError:
    logger.warning(
        "event=authorization_denied user_id=%s permission=%s",
        str(current_user.get("user_id") or "unknown"),
        permission,
    )
    return AppError(
        "You do not have permission to perform this action",
        status_code=403,
        code="FORBIDDEN",
    )


def authorize_permissions(current_user: dict, *permissions: str) -> None:
    """Enforce every permission and audit denied authorization attempts."""
    if not permissions:
        raise ValueError("At least one permission is required")
    for permission in permissions:
        if not has_permission(current_user, permission):
            raise _deny_permission(current_user, permission)


def require_permission(permission: str) -> Callable:
    """Return a dependency that enforces one resolved permission."""

    async def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if not has_permission(current_user, permission):
            raise _deny_permission(current_user, permission)
        return current_user

    return _dependency


def require_permissions(*permissions: str) -> Callable:
    """Require every listed permission, useful for aggregate read surfaces."""
    if not permissions:
        raise ValueError("At least one permission is required")

    async def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        authorize_permissions(current_user, *permissions)
        return current_user

    return _dependency
