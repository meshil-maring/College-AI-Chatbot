"""Canonical identity bootstrap and development-mode status."""
from fastapi import APIRouter, Depends
from app.config import settings
from app.core.errors import AppError
from app.core.security import get_current_user, resolve_primary_role

router = APIRouter()

@router.get("/api/v1/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """Phase 6.15.4 — canonical authenticated identity + role bootstrap.

    The role and tenant are resolved SERVER-SIDE from the authenticated
    JWT -> public.users -> user_roles -> roles chain (never from any
    client-supplied value). Existing Phase 5.4 response fields are preserved
    byte-for-byte; ``role`` (canonical, single) and ``institution_id`` (tenant
    context, None for platform-level accounts) are additive.

    An account whose active roles contain no supported role resolves to
    ``role: None`` — the frontend treats that as "no privileged UI".
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
    if payload["role"] == "faculty" and current_user.get("permissions_resolved") is True:
        from app.services.faculty.faculty_responsibilities import faculty_context
        from app.services.auth.authorization import resolve_institution_authorization_context
        context = resolve_institution_authorization_context(current_user, allowed_roles=("faculty",))
        try:
            payload["faculty_context"] = faculty_context({**current_user, "institution_id": str(context.institution_id)})
        except AppError as error:
            if error.status_code != 503 or error.code != "FACULTY_SCHEMA_UNAVAILABLE":
                raise
            # Identity and the institution grant have already been verified.
            # Missing optional faculty schema must not prevent sign-in or
            # manufacture any assignment or scoped responsibility permission.
            payload["faculty_context"] = {
                "responsibilities": [],
                "teaching_assignments": [],
                "responsibility_permissions": [],
            }
    return payload


@router.get("/api/v1/dev/auth/status")
def dev_auth_status():
    """DEVELOPMENT / TESTING ONLY.

    Public, unauthenticated flag so the frontend can decide whether to show
    the dev-only password recovery UI. Reveals nothing beyond a boolean and
    is a no-op outside development/testing (always False by default).
    """
    return {"dev_test_mode": settings.dev_test_mode}

