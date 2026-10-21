"""Security identity responsibilities."""

from fastapi import Header

from uuid import UUID

from app.config import settings
from app.core.errors import AppError
from app.core.security import tokens
from app.core.security.roles import resolve_primary_role


PUBLIC_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency — returns the authenticated application user."""
    if not authorization:
        raise AppError("Authentication required", status_code=401, code="AUTH_REQUIRED")

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        raise AppError(
            "Invalid authentication scheme",
            status_code=401,
            code="INVALID_SCHEME",
        )

    token = token.strip()
    if not token:
        raise AppError("Token missing", status_code=401, code="TOKEN_MISSING")
    if len(token) > settings.max_bearer_token_chars:
        raise AppError("Invalid token", status_code=401, code="INVALID_TOKEN")

    claims = tokens.verify_jwt(token)
    auth_user_id: str = claims["sub"]

    # Imported here to avoid circular imports
    from app.db.supabase import get_user_by_auth_id

    user = await get_user_by_auth_id(auth_user_id, include_permissions=True)
    if user is None:
        raise AppError(
            "No application user found for this account",
            status_code=404,
            code="USER_NOT_FOUND",
        )
    # The real database projection always includes ``status``. Keeping the
    # key-presence distinction permits deliberately minimal internal test
    # doubles while still failing closed if the production query ever returns
    # a null or non-active lifecycle value.
    if "status" in user and user.get("status") != "active":
        raise AppError(
            "This account is not active",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )

    role_assignments = user.get("role_assignments") or []
    primary_role = resolve_primary_role(user.get("roles", []))
    scoped_institutions = {
        str(grant["scope_id"])
        for grant in role_assignments
        if grant.get("role") == primary_role
        and grant.get("is_active", True)
        and grant.get("scope_type") == "institution"
        and grant.get("scope_id") is not None
    }
    # Non-student tenant scope comes only from the primary role assignment.
    # A student profile remains the legitimate fallback for the student role.
    if len(scoped_institutions) == 1:
        institution_id = next(iter(scoped_institutions))
    elif primary_role == "student":
        institution_id = user.get("student_institution_id", user.get("institution_id"))
    else:
        institution_id = None
    effective_permissions = set(user.get("effective_permissions") or ())
    active_staff_scopes = {
        str(grant.get("scope_id"))
        for grant in role_assignments
        if grant.get("role") == "staff"
        and grant.get("is_active", True)
        and grant.get("scope_type") == "institution"
        and grant.get("scope_id") is not None
    }
    for grant in user.get("direct_permission_grants") or ():
        if (
            institution_id is not None
            and str(institution_id) in active_staff_scopes
            and str(grant.get("institution_id")) == str(institution_id)
            and isinstance(grant.get("permission"), str)
        ):
            effective_permissions.add(grant["permission"])

    return {
        "user_id": user["user_id"],
        "auth_user_id": auth_user_id,
        "email": claims.get("email"),
        "auth_methods": claims.get("amr", []),
        "auth_session_id": claims.get("session_id"),
        "token_issued_at": claims.get("iat"),
        "roles": user.get("roles", []),
        "status": user.get("status"),
        "institution_id": institution_id,
        # Internal server-owned grants. They are never returned by /auth/me.
        "role_assignments": role_assignments,
        "effective_permissions": sorted(effective_permissions),
        "permissions_resolved": user.get("permissions_resolved", False),
    }
