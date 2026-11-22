"""Account status of institution Staff and Faculty: active, suspended, deactivated.

Access is decided by ``public.users.status``. Sign-in, every permission check
and the database commands require ``active``, so suspending or deactivating a
member blocks them everywhere at once. Suspension is a temporary pause that an
administrator lifts with reactivation; deactivation is for people who left.
Historical attendance, examination and audit records are never removed.

Only accounts whose roles are all Staff/Faculty may be changed here, so an
administrator cannot use this roster to lock out another administrator.
"""

from typing import Any, Literal
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_memberships as repo
from app.repositories.admin.admin_audit import record_admin_action
from app.schemas.admin.admin import AdminAuditLogCreate
from app.schemas.admin.admin_memberships import MembershipLifecycleResult

ALLOWED_ROLES = frozenset({"staff", "faculty"})
AccountStatus = Literal["active", "suspended", "deactivated"]

# The statuses each target may be reached from.
_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "active": ("inactive", "suspended", "deactivated"),
    "suspended": ("active",),
    "deactivated": ("active", "inactive", "suspended"),
}
_ACTION = {"active": "reactivated", "suspended": "suspended", "deactivated": "deactivated"}


def _member_roles(client, institution_id: UUID, user_id: UUID) -> set[str]:
    """All role names of the account; 404 unless it is Staff/Faculty here."""
    roles: set[str] = set()
    in_institution = False
    for grant in repo.list_user_grants(client, user_id):
        role_row = grant.get("roles") or {}
        role_name = role_row.get("name") if isinstance(role_row, dict) else None
        if role_name:
            roles.add(str(role_name))
        if (
            role_name in ALLOWED_ROLES
            and grant.get("scope_type") == "institution"
            and str(grant.get("scope_id")) == str(institution_id)
        ):
            in_institution = True
    if not in_institution:
        raise AppError("Staff or faculty member not found", 404, "MEMBERSHIP_NOT_FOUND")
    return roles


def set_status(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID, status: AccountStatus
) -> MembershipLifecycleResult:
    if status not in _TRANSITIONS:
        raise AppError("Unsupported account status", 422, "INVALID_MEMBERSHIP_STATUS")
    client = get_admin_client()
    user = repo.get_user(client, user_id)
    roles = _member_roles(client, institution_id, user_id) if user is not None else None
    if user is None or roles is None:
        raise AppError("Staff or faculty member not found", 404, "MEMBERSHIP_NOT_FOUND")
    if roles - ALLOWED_ROLES:
        raise AppError(
            "Accounts with other roles cannot be changed through this roster",
            409,
            "PROTECTED_ROLE",
        )
    current = str(user.get("status"))
    if current == status:
        return MembershipLifecycleResult(
            user_id=user_id, status=status, already_applied=True,
            message=f"Member is already {status}.",
        )
    if current not in _TRANSITIONS[status]:
        raise AppError(
            f"A {current} member cannot be {_ACTION[status]}", 409, "MEMBERSHIP_STATUS_CONFLICT"
        )
    if not repo.set_user_status(client, user_id, expected=_TRANSITIONS[status], status=status):
        raise AppError("Member status changed concurrently", 409, "MEMBERSHIP_STATUS_CONFLICT")
    role_label = "faculty" if "faculty" in roles else "staff"
    record_admin_action(
        client,
        AdminAuditLogCreate(
            actor_user_id=UUID(str(actor["user_id"])),
            institution_id=institution_id,
            action=f"{role_label}_{_ACTION[status]}",
            table_name="institution_membership_requests",
            record_id=str(user_id),
            record_data={"role": role_label, "status": status, "previous_status": current},
        ),
    )
    return MembershipLifecycleResult(
        user_id=user_id, status=status, already_applied=False, message=f"Member {status}.",
    )
