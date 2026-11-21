"""Administrator-chosen Staff or Faculty role for institution members.

The administrator confirms the role while approving a request and can switch
an approved member between Staff and Faculty later. Only these two roles can be
chosen here; administrator and platform roles are never reachable. A switch is
refused while something still depends on the current role.
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import member_roles as repo
from app.repositories.admin.admin_audit import record_admin_action
from app.schemas.admin.admin import AdminAuditLogCreate
from app.schemas.admin.admin_memberships import MemberRoleResult


def _audit(client, actor: dict, institution_id: UUID, action: str, record_id: str, data: dict) -> None:
    record_admin_action(
        client,
        AdminAuditLogCreate(
            actor_user_id=UUID(str(actor["user_id"])),
            institution_id=institution_id,
            action=action,
            table_name="user_roles",
            record_id=record_id,
            record_data=data,
        ),
    )


def _require_role(role: str) -> None:
    if role not in repo.MEMBER_ROLES:
        raise AppError("Choose Staff or Faculty", 422, "INVALID_MEMBERSHIP_ROLE")


def prepare_request_role(client, actor: dict, institution_id: UUID, row: dict[str, Any], role: str | None) -> None:
    """Apply the administrator's role choice to a request before approval."""
    if role is None or role == row.get("requested_role"):
        return
    _require_role(role)
    if row.get("status") != "pending":
        raise AppError(
            "This request is already decided. Change the role from the roster.",
            409,
            "MEMBERSHIP_REQUEST_ALREADY_DECIDED",
        )
    if not repo.set_pending_request_role(client, institution_id, row["request_id"], role):
        raise AppError("Membership request was decided concurrently", 409, "MEMBERSHIP_REQUEST_CONFLICT")
    _audit(
        client, actor, institution_id, "membership.request.role", str(row["request_id"]),
        {"from": row.get("requested_role"), "to": role},
    )


def change_role(actor: dict, institution_id: UUID, user_id: UUID, role: str) -> MemberRoleResult:
    """Switch an approved member between Staff and Faculty."""
    if not actor.get("user_id"):
        raise AppError("Verified actor required", 403, "FORBIDDEN")
    _require_role(role)
    client = get_admin_client()
    grant = repo.member_grant(client, institution_id, user_id)
    if grant is None:
        raise AppError("Staff or faculty member not found", 404, "MEMBER_NOT_FOUND")
    current = (grant.get("roles") or {}).get("name")
    if current == role:
        return MemberRoleResult(user_id=user_id, role=role, already_applied=True, message=f"Already {role.title()}.")
    if current == "faculty" and repo.is_current_department_head(client, institution_id, user_id):
        raise AppError(
            "This member is a Head of Department. End that appointment before making them Staff.",
            409,
            "MEMBER_IS_DEPARTMENT_HEAD",
        )
    if current == "staff" and repo.has_direct_staff_grants(client, institution_id, user_id):
        raise AppError(
            "Revoke this member's extra Staff permissions before making them Faculty.",
            409,
            "MEMBER_HAS_STAFF_PERMISSIONS",
        )
    ids = repo.role_ids(client)
    if role not in ids or current not in ids:
        raise AppError("The requested role is not configured", 500, "ROLE_NOT_CONFIGURED")
    if not repo.switch_role(
        client, institution_id=institution_id, user_id=user_id, from_role_id=ids[current], to_role_id=ids[role]
    ):
        raise AppError("This member's role was changed concurrently", 409, "MEMBER_ROLE_CONFLICT")
    _audit(client, actor, institution_id, "member.role.change", str(user_id), {"from": current, "to": role})
    return MemberRoleResult(
        user_id=user_id,
        role=role,
        already_applied=False,
        message=f"Role changed to {role.title()}. They will see the new workspace after signing in again.",
    )
