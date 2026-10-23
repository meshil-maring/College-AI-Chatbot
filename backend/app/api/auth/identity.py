"""Canonical identity bootstrap and development-mode status."""

from fastapi import APIRouter, Depends
from app.config import settings
from app.core.security import get_current_user, resolve_primary_role

router = APIRouter()


@router.get("/api/v1/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """Phase 6.15.4 â€” canonical authenticated identity + role bootstrap.

    The role and tenant are resolved SERVER-SIDE from the authenticated
    JWT -> public.users -> user_roles -> roles chain (never from any
    client-supplied value). Existing Phase 5.4 response fields are preserved
    byte-for-byte; ``role`` (canonical, single) and ``institution_id`` (tenant
    context, None for platform-level accounts) are additive.

    An account whose active roles contain no supported role resolves to
    ``role: None`` â€” the frontend treats that as "no privileged UI".
    """
    payload = {
        "authenticated": True,
        "user_id": current_user["user_id"],
        "auth_user_id": current_user["auth_user_id"],
        "email": current_user["email"],
        "role": resolve_primary_role(current_user.get("roles")),
        "institution_id": current_user.get("institution_id"),
        "effective_permissions": current_user.get("effective_permissions", []),
    }
    if (
        payload["role"] == "faculty"
        and current_user.get("permissions_resolved") is True
    ):
        from app.services.auth.authorization import (
            resolve_institution_authorization_context,
        )

        resolve_institution_authorization_context(
            current_user, allowed_roles=("faculty",)
        )
    return payload


@router.get("/api/v1/dev/auth/status")
def dev_auth_status():
    """DEVELOPMENT / TESTING ONLY.

    Public, unauthenticated flag so the frontend can decide whether to show
    the dev-only password recovery UI. Reveals nothing beyond a boolean and
    is a no-op outside development/testing (always False by default).
    """
    return {"dev_test_mode": settings.dev_test_mode}
