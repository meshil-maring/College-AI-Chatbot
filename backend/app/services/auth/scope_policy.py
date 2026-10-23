"""Organization and institution management policy."""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.repositories.platform import tenancy as tenancy_repo
from app.services.auth.scope_types import (
    PLATFORM,
    ORGANIZATION,
    INSTITUTION,
    user_organization_id,
    user_institution_id,
    _org_mismatch,
    _scope_forbidden,
    _tenant_mismatch,
)


def _database():
    # Keep the established authorization gateway shared by policy consumers.
    from app.services.auth import authorization

    return authorization.get_admin_client()


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
    if scope_type == PLATFORM:
        return
    raise _scope_forbidden()


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
        db = _database()
        inst_org = tenancy_repo.get_institution_organization(db, institution_id)
        assert_institution_in_organization(inst_org, user_org)
        return
    if scope_type == PLATFORM:
        return
    raise _scope_forbidden()


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
