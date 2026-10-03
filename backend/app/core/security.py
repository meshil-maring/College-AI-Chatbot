import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError, PyJWKError
from fastapi import Depends, Header
from typing import Callable
from uuid import UUID

from app.config import settings
from app.core.errors import AppError

_jwks_client: PyJWKClient | None = None
PUBLIC_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
"""Shared constant identity for public (unauthenticated) conversations.

Public chat routes use this UUID as the ``user_id`` for every new or
resumed conversation so that public messages are tenant-agnostic and can
never be read as belonging to any real authenticated user.
"""



# Tolerance (in seconds) for minor clock skew between the backend and the
# Supabase Auth token-issuing server.  A freshly issued JWT's ``iat`` (issued-at)
# claim can be a few seconds ahead of the local clock; without leeway PyJWT
# rejects it with ``ImmatureSignatureError`` (a subclass of ``InvalidTokenError``),
# which surfaces to the frontend as “The saved session could not be verified”.
_JWT_LEEWAY_SECONDS: int = 10


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwks_client


def verify_jwt(token: str) -> dict:
    """Verify a Supabase-issued JWT and return its claims."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={"require": ["sub", "exp", "aud"]},
            audience="authenticated",
            leeway=_JWT_LEEWAY_SECONDS,
        )
        return claims
    except ExpiredSignatureError:
        raise AppError("Token has expired", status_code=401, code="TOKEN_EXPIRED")
    except (InvalidTokenError, PyJWKError):
        # Phase 6.15.7 — never echo library internals (exception text can name
        # algorithms, claims, key material sources). Fixed user-safe message.
        raise AppError("Invalid token", status_code=401, code="INVALID_TOKEN")


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency — returns the authenticated application user."""
    if not authorization:
        raise AppError("Authentication required", status_code=401, code="AUTH_REQUIRED")

    if not authorization.startswith("Bearer "):
        raise AppError(
            "Invalid authentication scheme",
            status_code=401,
            code="INVALID_SCHEME",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppError("Token missing", status_code=401, code="TOKEN_MISSING")

    claims = verify_jwt(token)
    auth_user_id: str = claims["sub"]

    # Imported here to avoid circular imports
    from app.db.supabase import get_user_by_auth_id

    user = await get_user_by_auth_id(auth_user_id)
    if user is None:
        raise AppError(
            "No application user found for this account",
            status_code=404,
            code="USER_NOT_FOUND",
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

    return {
        "user_id": user["user_id"],
        "auth_user_id": auth_user_id,
        "email": claims.get("email"),
        "roles": user.get("roles", []),
        "status": user.get("status"),
        "institution_id": institution_id,
        # Internal server-owned grants. They are never returned by /auth/me.
        "role_assignments": role_assignments,
    }


# ============================================================================
# Tenant isolation helpers (institution_id is the tenant key)
# ============================================================================
#
# Multi-tenancy model:
#   College A  ->  institution_id = A   (tenant A)
#   College B  ->  institution_id = B   (tenant B)
#   Student of A -> institution_id = A (resolved from students.user_id)
#   Student of B -> institution_id = B
#
# Phase 7.20: `institution_id` in `current_user` is projected from the
# server-owned `user_roles` institution grant for every non-student role, and
# from the student profile for the student role. The helpers below are pure
# guards on that server-owned value.
#
# A tenant-less account is NOT privileged. `scope_tenant`/`assert_tenant_object`
# are defensive row guards that are only ever reached AFTER an authorization
# dependency (`require_institution_roles` / `require_super_admin`) has already
# resolved and validated an institution scope, so the tenantless branch can no
# longer be used to reach institution-admin operations.


def user_tenant_id(current_user: dict) -> UUID | None:
    """Return the authenticated user's tenant (institution_id), or None."""
    raw = current_user.get("institution_id") if current_user else None
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _tenant_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different institution",
        status_code=403,
        code="TENANT_MISMATCH",
    )


def scope_tenant(
    current_user: dict,
    requested: UUID | str | None,
) -> UUID | None:
    """Resolve the effective tenant for a request that carries an institution id.

    * Tenant-bound user + requested institution  -> must match, else 403.
    * Tenant-bound user + no requested institution -> own tenant.
    * Platform-level user (no tenant)            -> requested passed through.
    """
    tenant = user_tenant_id(current_user)
    if tenant is None:
        # Platform-level account: pass the requested institution through.
        return requested if not isinstance(requested, str) else UUID(requested)
    if requested is not None and UUID(str(requested)) != tenant:
        raise _tenant_mismatch()
    return tenant


def assert_tenant_object(
    current_user: dict,
    institution_id: UUID | str | None,
) -> None:
    """Guard a fetched/created row against cross-tenant access.

    Rows with institution_id=None are global and visible to everyone.
    Tenant-bound users may only access rows belonging to their own tenant.
    """
    tenant = user_tenant_id(current_user)
    if tenant is None or institution_id is None:
        return
    if UUID(str(institution_id)) != tenant:
        raise _tenant_mismatch()


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
        from app.services.authorization import (
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


def user_tenant_id(current_user: dict) -> UUID | None:
    """Return the authenticated user's tenant (institution_id), or None."""
    raw = current_user.get("institution_id") if current_user else None
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


# ============================================================================
# Phase 6.15.4 — Canonical role resolution
# ============================================================================
# The role names below are the canonical identities that /auth/me may return
# after resolving the roles table through the existing server-side chain.
# Phase 7.11 added ``super_admin`` recognition; Phase 7.12 persists it and
# authorizes it through a separate, fresh platform-scope check. It remains
# deliberately absent from every tenant-level require_roles check.
SUPPORTED_ROLES: tuple[str, ...] = (
    "super_admin",
    "admin",
    "staff",
    "faculty",
    "student",
)

# Resolution precedence when an account holds several active roles. The most
# privileged role wins. A server-assigned super_admin identity selects only
# the isolated platform placeholder; tenant endpoints remain independently
# guarded by their existing role dependencies.
_ROLE_PRECEDENCE: dict[str, int] = {
    role: index for index, role in enumerate(SUPPORTED_ROLES)
}


def resolve_primary_role(roles: list[str] | tuple[str, ...] | None) -> str | None:
    """Resolve the canonical primary role from the server-side role list.

    Returns the highest-precedence SUPPORTED role, or None when the account
    holds no supported role (unknown/unsupported roles are never reported —
    the caller treats None as "no privileged UI").
    """
    if not roles:
        return None
    supported = [
        _ROLE_PRECEDENCE[role]
        for role in roles
        if role in _ROLE_PRECEDENCE
    ]
    if not supported:
        return None
    return SUPPORTED_ROLES[min(supported)]

