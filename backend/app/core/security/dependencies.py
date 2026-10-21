"""Security dependencies responsibilities."""

from fastapi import Depends

from typing import Callable

from app.core.errors import AppError
from app.core.security.identity import get_current_user
from app.core.security.permissions import has_permission, _deny_permission
from app.core.security.roles import resolve_primary_role


def require_roles(*allowed: str) -> Callable:
    """Return a FastAPI dependency that enforces role membership.

    Raises 401 for unauthenticated requests (delegated to get_current_user).
    Raises 403 when the authenticated user holds none of the allowed roles.
    """
    allowed_set = frozenset(allowed)

    async def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if not allowed_set.intersection(current_user.get("roles", [])):
            raise AppError(
                "You do not have permission to perform this action",
                status_code=403,
                code="FORBIDDEN",
            )
        return current_user

    return _dependency


def require_institution_permission(permission: str, *allowed_roles: str) -> Callable:
    """Require an institution-scoped role and one permission for that scope."""
    institution_dependency = require_institution_roles(*allowed_roles)

    async def _dependency(
        current_user: dict = Depends(institution_dependency),
    ) -> dict:
        if not has_permission(current_user, permission):
            raise _deny_permission(current_user, permission)
        return current_user

    return _dependency


def require_institution_roles(*allowed: str) -> Callable:
    """Require an active institution-scoped grant for one allowed role.

    Unlike the legacy ``require_roles`` helper, this dependency never treats a
    missing tenant as platform authority. Scope is read from the server-owned
    role assignments loaded by ``get_current_user`` and institution lifecycle
    is verified for every request. The returned user copy is pinned to the
    resolved institution so existing resource guards receive authoritative
    scope without accepting a request/body/query tenant as authorization.
    """

    allowed_roles = tuple(allowed)

    async def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        from app.services.auth.authorization import (
            resolve_institution_authorization_context,
        )

        context = resolve_institution_authorization_context(
            current_user,
            allowed_roles=allowed_roles,
        )
        scoped_user = dict(current_user)
        scoped_user["institution_id"] = str(context.institution_id)
        scoped_user["authorization_context"] = context
        return scoped_user

    return _dependency


async def require_super_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Authorize the canonical, active, platform-scoped super_admin only.

    Role and scope are resolved from the verified JWT's application user and
    database grants. Tenant ids, URL values, frontend state, and JWT metadata
    supplied by a client do not participate in this decision.
    """
    if resolve_primary_role(current_user.get("roles")) != "super_admin":
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    # Use a fresh database read on every protected request. This is deliberately
    # not inferred from a tenant context or JWT metadata, and makes revocation
    # effective without waiting for the browser session to expire.
    from app.db.supabase import get_super_admin_authorization

    authorization = await get_super_admin_authorization(current_user["auth_user_id"])
    if authorization is None or authorization.get("status") != "active":
        raise AppError(
            "This account is not active",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )
    if not authorization.get("has_platform_grant", False):
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    return current_user
