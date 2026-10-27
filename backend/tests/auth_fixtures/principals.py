"""Explicit resolved identities for legacy tests that mock the database boundary."""

from copy import deepcopy

from app.core.permission_defaults import DEFAULT_ROLE_PERMISSIONS
from app.core.security.roles import resolve_primary_role
from app.core.security.scoped_permissions import primary_scope_permissions


def institution_grant(role, institution_id, permissions=None):
    return {
        "role": role,
        "scope_type": "institution" if institution_id else "platform",
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
        "permissions": sorted(DEFAULT_ROLE_PERMISSIONS.get(role, ())) if permissions is None else permissions,
    }


def resolved_principal(principal):
    """Model a successful permission query; preserve explicit empty/revoked grants.

    Use only where a test replaces get_user_by_auth_id or the authenticated
    dependency. Production authentication and negative resolution tests continue
    to enforce their existing fail-closed behavior.
    """
    user = deepcopy(principal)
    user.setdefault("role_assignments", [
        institution_grant(role, user.get("institution_id")) for role in user.get("roles", [])
    ])
    for grant in user.get("role_assignments", []):
        grant.setdefault("permissions", sorted(DEFAULT_ROLE_PERMISSIONS.get(grant.get("role"), ())))
    user.setdefault("permissions_resolved", True)
    user.setdefault("scoped_permissions_resolved", True)
    user.setdefault("effective_permissions", sorted(primary_scope_permissions(user, resolve_primary_role(user.get("roles", [])))))
    return user
