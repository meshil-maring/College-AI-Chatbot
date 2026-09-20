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

    return {
        "user_id": user["user_id"],
        "auth_user_id": auth_user_id,
        "email": claims.get("email"),
        "roles": user.get("roles", []),
        "institution_id": user.get("institution_id"),
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
# Accounts WITH a tenant may only ever touch rows belonging to their own
# institution. Accounts WITHOUT a tenant (platform-level, e.g. admins without
# a students profile) keep the previous unrestricted behaviour.


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
def user_tenant_id(current_user: dict) -> UUID | None:
    """Return the authenticated user's tenant (institution_id), or None."""
    raw = current_user.get("institution_id") if current_user else None
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


# ============================================================================
# Phase 6.15.4 — Canonical role resolution
# ============================================================================
# The role names below are the EXISTING Phase 6.6 RBAC role names (the only
# roles the database can contain — see roles table and require_roles usage).
# No new role is introduced and no authorization rule changes: this is a
# read-only projection over the roles already resolved server-side by
# get_current_user -> get_user_by_auth_id -> user_roles -> roles.
SUPPORTED_ROLES: tuple[str, ...] = ("admin", "staff", "faculty", "student")

# Resolution precedence when an account holds several active roles. The most
# privileged operational role wins; "admin" first keeps the existing
# /admin/* behavior identical for multi-role accounts.
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

