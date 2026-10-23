"""Fail-closed platform route policies and account authority dependency."""

import logging

from fastapi import Depends, Request

from app.core.errors import AppError
from app.core.security import (
    authorize_permissions,
    get_current_user,
    require_super_admin,
)

logger = logging.getLogger(__name__)
_SUPER_ADMIN = require_super_admin
_PLATFORM_ROUTE_PERMISSIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("GET", "/platform/me"): ("platform.read",),
    ("GET", "/platform/institutions"): ("platform.read",),
    ("POST", "/platform/institutions"): ("platform.manage",),
    ("GET", "/platform/institutions/{institution_id}"): ("platform.read",),
    ("PATCH", "/platform/institutions/{institution_id}"): ("platform.manage",),
    ("POST", "/platform/institutions/{institution_id}/suspend"): ("platform.manage",),
    ("POST", "/platform/institutions/{institution_id}/activate"): ("platform.manage",),
    ("POST", "/platform/institutions/{institution_id}/admins"): ("platform.manage",),
    ("POST", "/platform/institutions/{institution_id}/admins/invitations"): (
        "platform.manage",
    ),
    ("GET", "/platform/institutions/{institution_id}/admins/roster"): (
        "platform.read",
    ),
    (
        "POST",
        "/platform/institutions/{institution_id}/admins/invitations/{invitation_id}/cancel",
    ): ("platform.manage",),
    (
        "POST",
        "/platform/institutions/{institution_id}/admins/invitations/{invitation_id}/resend",
    ): ("platform.manage",),
    ("POST", "/platform/admin-invitations/expire-sweep"): ("platform.manage",),
    ("POST", "/platform/institutions/{institution_id}/admins/{user_id}/revoke"): (
        "platform.manage",
    ),
    ("GET", "/platform/audit"): ("platform.audit.read",),
    ("POST", "/platform/super-admins/invitations"): ("platform.manage",),
    ("GET", "/platform/super-admins/invitations"): ("platform.read",),
    ("POST", "/platform/super-admins/invitations/{invitation_id}/cancel"): (
        "platform.manage",
    ),
}


async def _authorize_platform_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> None:
    route = request.scope.get("route")
    route_path = getattr(route, "path", "")
    platform_path_index = route_path.rfind("/platform")
    normalized_path = (
        route_path[platform_path_index:] if platform_path_index >= 0 else ""
    )
    permissions = _PLATFORM_ROUTE_PERMISSIONS.get((request.method, normalized_path))
    if permissions is None:
        logger.error(
            "event=authorization_policy_missing method=%s path=%s",
            request.method,
            normalized_path or "unknown",
        )
        raise AppError(
            "You do not have permission to perform this action",
            status_code=403,
            code="FORBIDDEN",
        )
    authorize_permissions(current_user, *permissions)
