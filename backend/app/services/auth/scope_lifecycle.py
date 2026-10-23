"""Tenant lifecycle and scope-consistency validation."""

from typing import Any
from uuid import UUID

from app.repositories.platform import tenancy as tenancy_repo
from app.services.auth.scope_types import (
    PLATFORM,
    ORGANIZATION,
    INSTITUTION,
    ACTIVE_STATUS,
    PENDING_STATUS,
    user_organization_id,
    user_institution_id,
    _scope_missing,
    _scope_inconsistent,
    _tenant_inactive,
    _organization_inactive,
)

_ALLOWED_SCOPE_TYPES = (PLATFORM, ORGANIZATION, INSTITUTION)


def _profile_institution_id(current_user: dict[str, Any] | None) -> UUID | None:
    """The tenant bound to the user's students profile, if any (server-side)."""
    raw = current_user.get("institution_id") if current_user else None
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def assert_scope_consistency(
    current_user: dict[str, Any] | None,
    authorization_context: dict[str, Any],
) -> None:
    """Reject inconsistent or orphaned scope records (fail closed, §8).

    * missing scope entirely                     -> 403 SCOPE_MISSING
    * unknown scope_type value                   -> 403 SCOPE_INCONSISTENT
    * organization scope without an organization -> 403 SCOPE_INCONSISTENT
    * institution scope without an institution   -> 403 SCOPE_INCONSISTENT
    * institution scope != user's own profile
      institution (tenant-bound accounts)        -> 403 SCOPE_INCONSISTENT
    * platform scope on a tenant-bound account   -> 403 SCOPE_INCONSISTENT
    """
    scope_type = authorization_context.get("scope_type")
    if scope_type is None:
        raise _scope_missing()
    if scope_type not in _ALLOWED_SCOPE_TYPES:
        raise _scope_inconsistent()

    if (
        scope_type == ORGANIZATION
        and user_organization_id(authorization_context) is None
    ):
        # Orphaned organization scope: the role row exists but names no tenant.
        raise _scope_inconsistent()

    if scope_type == INSTITUTION:
        scope_inst = user_institution_id(authorization_context)
        if scope_inst is None:
            # Orphaned institution scope.
            raise _scope_inconsistent()
        profile_inst = _profile_institution_id(current_user)
        if profile_inst is not None and profile_inst != scope_inst:
            # The scope points at another tenant than the user's own profile.
            raise _scope_inconsistent()

    if scope_type == PLATFORM:
        if _profile_institution_id(current_user) is not None:
            # A tenant-bound account can never hold platform (unrestricted)
            # scope: the locked resolution rule is tenant-bound -> institution.
            raise _scope_inconsistent()


def assert_tenant_context_active(
    db: Any,
    authorization_context: dict[str, Any],
) -> None:
    """Deny authorization when the resolved tenant is not usable (§9).

    Reads the tenant lifecycle status from trusted server-side rows:

    * INSTITUTION scope -> institutions row must exist with status == 'active'
      AND is_active (the Phase 6.13 trigger derives is_active from status, so
      pending/rejected/suspended all fail closed).
    * ORGANIZATION scope -> organizations row must exist with status in
      {'pending', 'active'} — a pending organization may still be managed by
      its own admin while awaiting the platform decision, but rejected and
      suspended (inactive) organizations fail closed.
    * PLATFORM scope -> no tenant to check (previous behaviour preserved).
    """
    scope_type = authorization_context.get("scope_type")
    if scope_type == INSTITUTION:
        institution_id = user_institution_id(authorization_context)
        if institution_id is None:
            raise _tenant_inactive()
        institution = tenancy_repo.get_institution_by_id(db, institution_id)
        if (
            institution is None
            or institution.get("status") != ACTIVE_STATUS
            or not institution.get("is_active", False)
        ):
            raise _tenant_inactive()
    elif scope_type == ORGANIZATION:
        organization_id = user_organization_id(authorization_context)
        if organization_id is None:
            raise _organization_inactive()
        organization = tenancy_repo.get_organization_by_id(db, organization_id)
        if organization is None or organization.get("status") not in (
            PENDING_STATUS,
            ACTIVE_STATUS,
        ):
            raise _organization_inactive()


def assert_active_tenant_context(
    db: Any,
    current_user: dict[str, Any] | None,
    authorization_context: dict[str, Any],
) -> None:
    """Combined Phase 6.13.7 guard: consistency first, then tenant lifecycle."""
    assert_scope_consistency(current_user, authorization_context)
    assert_tenant_context_active(db, authorization_context)
