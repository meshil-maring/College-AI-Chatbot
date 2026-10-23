"""Server-owned account scope resolution and public policy contract."""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.platform import tenancy as tenancy_repo
from app.services.auth.scope_types import (
    AuthorizationContext,
    PLATFORM,
    ORGANIZATION,
    INSTITUTION,
    ACTIVE_STATUS,
    user_organization_id,
    user_institution_id,
    _scope_forbidden,
    _scope_missing,
    _scope_inconsistent,
    _tenant_inactive,
)
from app.services.auth.scope_policy import (
    assert_institution_in_organization,
    assert_can_manage_organization,
    assert_can_manage_institution,
    assert_can_decide_join_request,
    _assert_platform_authority,
)
from app.services.auth.scope_lifecycle import (
    assert_scope_consistency,
    assert_tenant_context_active,
    assert_active_tenant_context,
)


def resolve_institution_authorization_context(
    current_user: dict[str, Any],
    *,
    allowed_roles: tuple[str, ...],
) -> AuthorizationContext:
    """Resolve one active institution grant and fail closed otherwise.

    Role assignments originate in the ``public.users -> user_roles -> roles``
    projection loaded after JWT verification. Client input never participates.
    A platform or organization grant is not an institution grant, and a
    missing/ambiguous institution scope is never interpreted as unrestricted.
    """

    user_id = current_user.get("user_id")
    if not user_id:
        raise AppError(
            "Invalid authenticated user context",
            status_code=400,
            code="INVALID_USER_CONTEXT",
        )

    if current_user.get("status") != ACTIVE_STATUS:
        raise AppError(
            "This account is not active",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )

    active_roles = set(current_user.get("roles") or [])
    if not active_roles.intersection(allowed_roles):
        raise _scope_forbidden()

    assignments = current_user.get("role_assignments")
    if not isinstance(assignments, list):
        raise _scope_missing()

    matching_role_grants = [
        grant
        for grant in assignments
        if isinstance(grant, dict)
        and grant.get("role") in allowed_roles
        and grant.get("role") in active_roles
        and grant.get("is_active", True)
    ]
    institution_grants = [
        grant
        for grant in matching_role_grants
        if grant.get("scope_type") == INSTITUTION and grant.get("scope_id") is not None
    ]
    if not institution_grants:
        if matching_role_grants:
            # The role exists, but its organization/platform/missing scope is
            # not sufficient for a University Admin operation.
            raise _scope_forbidden()
        raise _scope_missing()

    institution_ids = {UUID(str(grant["scope_id"])) for grant in institution_grants}
    if len(institution_ids) != 1:
        raise _scope_inconsistent()
    institution_id = next(iter(institution_ids))

    # Preserve the dependency's declared precedence (admin before staff for
    # the approval surface) while requiring that exact role's institution row.
    selected_role = next(
        role
        for role in allowed_roles
        if any(
            grant.get("role") == role and UUID(str(grant["scope_id"])) == institution_id
            for grant in institution_grants
        )
    )

    db = get_admin_client()
    institution = tenancy_repo.get_institution_by_id(db, institution_id)
    if (
        institution is None
        or institution.get("status") != ACTIVE_STATUS
        or not institution.get("is_active", False)
    ):
        raise _tenant_inactive()

    return AuthorizationContext(
        user_id=UUID(str(user_id)),
        role=selected_role,
        scope_type=INSTITUTION,
        institution_id=institution_id,
        is_active=True,
    )


def resolve_authorization_context(current_user: dict[str, Any]) -> dict[str, Any]:
    """Resolve the full Phase 6.13 scope context for an authenticated user.

    Server-side chain: JWT ``sub`` -> users.id -> user_roles.user_id (+scope).
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
    for row in sorted(
        active, key=lambda r: priority.get(r.get("scope_type") or PLATFORM, 3)
    ):
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
