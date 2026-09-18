"""Phase 6.13 — Role + Scope authorization service.

ADDITIVE authorization layer on top of the locked Phase 6.6 RBAC primitives.
The existing ``get_current_user`` / ``require_roles`` / ``scope_tenant`` /
``assert_tenant_object`` helpers are UNCHANGED and remain the primary
boundary; this module adds the organization/institution SCOPE dimension:

    User -> Authentication -> Organization -> Institution -> Role -> Scope
         -> Permission -> Resource/Data -> AI/RAG

Scope model (stored on the existing ``user_roles`` rows):

    scope_type = 'platform'      -> no tenant restriction (previous behaviour)
    scope_type = 'organization'  -> admin of ONE organization (all its institutions)
    scope_type = 'institution'   -> bound to ONE institution (tenant isolation)

Authorization context resolution is ALWAYS server-side: the scope columns are
read from ``user_roles`` by ``user_id`` derived from the verified JWT ``sub``.
No client-supplied role / scope / organization / institution field is ever
trusted.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import tenancy as tenancy_repo

PLATFORM = "platform"
ORGANIZATION = "organization"
INSTITUTION = "institution"


def resolve_authorization_context(current_user: dict[str, Any]) -> dict[str, Any]:
    """Resolve the full Phase 6.13 scope context for an authenticated user.

    Server-side chain: JWT ``sub`` -> users.user_id -> user_roles(+scope).
    The institution fallback preserves the locked Phase 6 behaviour for
    student accounts whose user_roles scope columns pre-date backfill.

    Returns a dict with: user_id, roles, scope_type, scope_id,
    organization_id, institution_id.
    """
    user_id = current_user.get("user_id")
    if not user_id:
        raise AppError(
            "Invalid authenticated user context",
            status_code=400,
            code="INVALID_USER_CONTEXT",
        )

    db = get_admin_client()
    role_rows = tenancy_repo.get_user_role_scope_rows(db, user_id)

    active = [row for row in role_rows if row.get("is_active", True)]
    roles = [row["role_name"] for row in active if row.get("role_name")]

    context: dict[str, Any] = {
        "user_id": str(user_id),
        "email": current_user.get("email"),
        "roles": roles,
        "scope_type": None,
        "scope_id": None,
        "organization_id": None,
        "institution_id": current_user.get("institution_id"),
    }

    # Prefer the most privileged scope for the context summary.
    # Rows written before the Phase 6.13 scope backfill (scope_type IS NULL) are
    # NOT classified here: they are derived AFTER the loop from the locked
    # tenant resolution, exactly like the migration backfill rule
    # ("tenant-bound -> institution, otherwise platform"). This is what stops a
    # legacy institution-scoped account from being silently widened to
    # platform (unrestricted) authority.
    priority = {ORGANIZATION: 0, INSTITUTION: 1, PLATFORM: 2}
    legacy_unscoped_row = False
    for row in sorted(active, key=lambda r: priority.get(r.get("scope_type") or PLATFORM, 3)):
        if row.get("scope_type") is None:
            legacy_unscoped_row = True
            continue
        scope_type = row["scope_type"]
        if context["scope_type"] is None:
            context["scope_type"] = scope_type
            raw_scope_id = row.get("scope_id")
            context["scope_id"] = str(raw_scope_id) if raw_scope_id else None
        if scope_type == ORGANIZATION and context["organization_id"] is None:
            raw_org = row.get("scope_id") or row.get("scope_organization_id")
            context["organization_id"] = str(raw_org) if raw_org else None
        if scope_type == INSTITUTION:
            raw_inst = row.get("scope_id")
            if raw_inst:
                context["institution_id"] = str(raw_inst)
                if context["organization_id"] is None:
                    org = tenancy_repo.get_institution_organization(db, raw_inst)
                    context["organization_id"] = str(org) if org else None
            if context["organization_id"] is None:
                raw_org = row.get("scope_organization_id")
                context["organization_id"] = str(raw_org) if raw_org else None

    # Backward compatibility: a student (or any tenant-bound user) whose
    # user_roles scope columns are not yet populated still resolves their
    # institution from the locked Phase 6 tenant resolution.
    if context["scope_type"] is None and context["institution_id"] is not None:
        context["scope_type"] = INSTITUTION
        context["scope_id"] = context["institution_id"]
        org = tenancy_repo.get_institution_organization(db, context["institution_id"])
        context["organization_id"] = str(org) if org else None
    elif context["scope_type"] is None and legacy_unscoped_row:
        # Tenant-less legacy row: platform scope, i.e. the previous behaviour.
        context["scope_type"] = PLATFORM

    return context


def user_organization_id(authorization_context: dict[str, Any]) -> UUID | None:
    """Return the user's organization id from their resolved context, or None."""
    raw = authorization_context.get("organization_id")
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def user_institution_id(authorization_context: dict[str, Any]) -> UUID | None:
    """Return the user's institution id from their resolved context, or None."""
    raw = authorization_context.get("institution_id")
    if raw is None:
        return None
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _org_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different organization",
        status_code=403,
        code="ORGANIZATION_MISMATCH",
    )


def _scope_forbidden() -> AppError:
    return AppError(
        "You do not have permission to perform this action",
        status_code=403,
        code="FORBIDDEN",
    )


def assert_institution_in_organization(
    institution_organization_id: UUID | str | None,
    organization_id: UUID | str | None,
) -> None:
    """Reject a cross-organization access attempt (defense in depth).

    Even when a row's denormalized organization_id were wrong in the database,
    the Phase 6.13 trigger ``phase613_assert_child_organization`` already
    prevents it; this server-side check is the application-layer backstop.
    """
    if institution_organization_id is None or organization_id is None:
        raise _org_mismatch()
    if UUID(str(institution_organization_id)) != UUID(str(organization_id)):
        raise _org_mismatch()


# ============================================================================
# Admin authority checks (org admin vs institution admin vs platform)
# ============================================================================


def assert_can_manage_organization(
    current_user: dict[str, Any],
    authorization_context: dict[str, Any],
    organization_id: UUID | str,
) -> None:
    """Only the organization's own org-scoped admin or a platform admin.

    Organization-scoped admins manage their OWN organization (join codes,
    institution lists, etc.) but cannot approve/reject it — that is a
    PLATFORM-level action enforced separately by ``_assert_platform_authority``
    inside ``decide_organization``.
    """
    if "admin" not in authorization_context.get("roles", []):
        raise _scope_forbidden()
    scope_type = authorization_context.get("scope_type")
    if scope_type == ORGANIZATION:
        user_org = user_organization_id(authorization_context)
        if user_org is None or user_org != UUID(str(organization_id)):
            raise _org_mismatch()
        return
    if scope_type == INSTITUTION:
        # Institution admins manage THEIR institution, never the organization.
        raise _scope_forbidden()
    # platform scope: unrestricted (previous behaviour preserved)
    return


def _assert_platform_authority(
    authorization_context: dict[str, Any],
) -> None:
    """Only PLATFORM-scoped admins may perform organization approval/rejection.

    Organization-scoped admins can manage their own organization but can NEVER
    approve/reject it — that is a platform-level decision enforced here.
    Institution-scoped admins and non-admin roles are also rejected.
    """
    if "admin" not in authorization_context.get("roles", []):
        raise _scope_forbidden()
    if authorization_context.get("scope_type") != PLATFORM:
        raise _scope_forbidden()
    return


def assert_can_manage_institution(
    current_user: dict[str, Any],
    authorization_context: dict[str, Any],
    institution_id: UUID | str,
) -> None:
    """Institution admin of THIS institution, org admin of its organization,
    or a platform admin. Everyone else is rejected."""
    if "admin" not in authorization_context.get("roles", []):
        raise _scope_forbidden()
    scope_type = authorization_context.get("scope_type")
    if scope_type == INSTITUTION:
        user_inst = user_institution_id(authorization_context)
        if user_inst is None or user_inst != UUID(str(institution_id)):
            raise _tenant_mismatch()
        return
    if scope_type == ORGANIZATION:
        user_org = user_organization_id(authorization_context)
        if user_org is None:
            raise _org_mismatch()
        db = get_admin_client()
        inst_org = tenancy_repo.get_institution_organization(db, institution_id)
        assert_institution_in_organization(inst_org, user_org)
        return
    # platform scope: unrestricted (previous behaviour preserved)
    return


def assert_can_decide_join_request(
    authorization_context: dict[str, Any],
    join_request: dict[str, Any],
) -> None:
    """ONLY the owning organization's admin (or a platform admin) decides.

    Institution-scoped users can NEVER approve/reject organization joins, and
    no other role can either — this is the exclusive authority of the
    organization admin per the Phase 6.13 approval workflow.
    """
    if "admin" not in authorization_context.get("roles", []):
        raise _scope_forbidden()
    scope_type = authorization_context.get("scope_type")
    request_org = join_request.get("organization_id")
    if scope_type == ORGANIZATION:
        user_org = user_organization_id(authorization_context)
        if user_org is None or str(user_org) != str(request_org):
            raise _org_mismatch()
        return
    if scope_type == PLATFORM:
        # Platform admins keep the previous unrestricted behaviour.
        return
    # Institution-scoped users and any other role can never approve joins.
    raise _org_mismatch()


def _tenant_mismatch() -> AppError:
    return AppError(
        "This resource belongs to a different institution",
        status_code=403,
        code="TENANT_MISMATCH",
    )
# ============================================================================
# Phase 6.13.7 — Role + Scope Enforcement (ADDITIVE primitives)
# ============================================================================
# These helpers complete the fail-closed enforcement chain WITHOUT changing any
# locked Phase 6.6 / 6.13 primitive above:
#
#   1. assert_scope_consistency()       — §8: reject inconsistent/orphaned
#                                         scope records (scope_type without a
#                                         scope id, scope pointing at another
#                                         tenant than the user's own profile,
#                                         tenant-bound accounts claiming
#                                         platform scope, unknown scope types,
#                                         or NO scope at all).
#   2. assert_tenant_context_active()   — §9: deny authorization when the
#                                         resolved tenant is not usable
#                                         (institution: must be 'active' with
#                                         is_active; pending/rejected/suspended
#                                         all fail closed. organization: must
#                                         be 'pending' or 'active'; rejected/
#                                         suspended/unknown fail closed).
#   3. assert_active_tenant_context()   — 1 + 2 combined; the single guard the
#                                         decision services call AFTER the
#                                         existing role/scope guards so the
#                                         established error codes (FORBIDDEN,
#                                         TENANT_MISMATCH, ORGANIZATION_MISMATCH)
#                                         keep their meaning.

ACTIVE_STATUS = "active"
PENDING_STATUS = "pending"

_ALLOWED_SCOPE_TYPES = (PLATFORM, ORGANIZATION, INSTITUTION)


def _scope_missing() -> AppError:
    return AppError(
        "No authorization scope could be resolved for this account",
        status_code=403,
        code="SCOPE_MISSING",
    )


def _scope_inconsistent() -> AppError:
    return AppError(
        "Authorization context is inconsistent or incomplete",
        status_code=403,
        code="SCOPE_INCONSISTENT",
    )


def _tenant_inactive() -> AppError:
    return AppError(
        "This institution is not active",
        status_code=403,
        code="TENANT_INACTIVE",
    )


def _organization_inactive() -> AppError:
    return AppError(
        "This organization is not active",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
    )


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

    if scope_type == ORGANIZATION and user_organization_id(authorization_context) is None:
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
    # PLATFORM scope: no tenant lifecycle to enforce.


def assert_active_tenant_context(
    db: Any,
    current_user: dict[str, Any] | None,
    authorization_context: dict[str, Any],
) -> None:
    """Combined Phase 6.13.7 guard: consistency first, then tenant lifecycle."""
    assert_scope_consistency(current_user, authorization_context)
    assert_tenant_context_active(db, authorization_context)
