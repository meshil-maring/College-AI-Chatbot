"""Administrator-chosen departments for institution Staff and Faculty.

Applicants do not pick their own department. The administrator chooses it when
approving a membership request, and can change it later from the roster. Every
write checks the department's institution and the member's active Staff or
Faculty grant in the administrator's institution; the database trigger repeats
the institution check.
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_memberships as membership_repo
from app.repositories.admin import member_departments as repo
from app.repositories.admin.admin_audit import record_admin_action
from app.schemas.admin.admin import AdminAuditLogCreate
from app.schemas.admin.admin_memberships import (
    MemberDepartmentResult,
    MembershipDecisionResult,
    MembershipRoster,
)
from app.services.admin import admin_memberships, member_roles

MEMBER_ROLES = frozenset({"staff", "faculty"})


def _require_department(client, institution_id: UUID, department_id: UUID) -> dict[str, Any]:
    department = repo.get_department(client, institution_id, department_id)
    if department is None:
        raise AppError("Department not found in this institution", 404, "DEPARTMENT_NOT_FOUND")
    if department.get("is_active") is False:
        raise AppError("This department is inactive", 422, "DEPARTMENT_INACTIVE")
    return department


def _require_member(client, institution_id: UUID, user_id: UUID | str) -> None:
    for grant in membership_repo.list_user_grants(client, user_id):
        role = (grant.get("roles") or {}).get("name")
        if (
            grant.get("scope_type") == "institution"
            and str(grant.get("scope_id")) == str(institution_id)
            and role in MEMBER_ROLES
        ):
            return
    raise AppError("Staff or faculty member not found", 404, "MEMBER_NOT_FOUND")


def _save(client, actor: dict, institution_id: UUID, user_id, department: dict) -> MemberDepartmentResult:
    repo.upsert_assignment(
        client,
        institution_id=institution_id,
        user_id=user_id,
        department_id=department["department_id"],
        assigned_by=actor["user_id"],
    )
    record_admin_action(
        client,
        AdminAuditLogCreate(
            actor_user_id=UUID(str(actor["user_id"])),
            institution_id=institution_id,
            action="member.department.assign",
            table_name=repo.TABLE,
            record_id=str(user_id),
            record_data={"department_id": str(department["department_id"])},
        ),
    )
    return MemberDepartmentResult(
        user_id=UUID(str(user_id)),
        department_id=UUID(str(department["department_id"])),
        department_code=str(department.get("code") or ""),
        department_name=str(department.get("name") or ""),
        message=f"Department set to {department.get('name')}.",
    )


def assign(actor: dict, institution_id: UUID, user_id: UUID, department_id: UUID) -> MemberDepartmentResult:
    """Set or change the department of an existing Staff/Faculty member."""
    if not actor.get("user_id"):
        raise AppError("Verified actor required", 403, "FORBIDDEN")
    client = get_admin_client()
    department = _require_department(client, institution_id, department_id)
    _require_member(client, institution_id, user_id)
    return _save(client, actor, institution_id, user_id, department)


def approve_request(
    actor: dict,
    institution_id: UUID,
    request_id: UUID,
    *,
    department_id: UUID | None,
    reason: str | None,
    role: str | None = None,
) -> MembershipDecisionResult:
    """Approve a membership request as Staff or Faculty, in a chosen department.

    The department is validated before anything is approved. A department is
    required for a pending request; retrying sign-in setup for an already
    approved request may omit it.
    """
    client = get_admin_client()
    row = membership_repo.get_request_for_institution(client, request_id, institution_id)
    if row is None:
        raise AppError("Membership request not found", 404, "MEMBERSHIP_REQUEST_NOT_FOUND")
    if row.get("status") == "pending" and department_id is None:
        raise AppError("Choose a department before approving", 422, "DEPARTMENT_REQUIRED")
    department = _require_department(client, institution_id, department_id) if department_id else None
    # The administrator may approve the applicant as the other member role.
    member_roles.prepare_request_role(client, actor, institution_id, row, role)
    result = admin_memberships.decide_request(
        actor, institution_id, request_id, approve=True, reason=reason
    )
    if department is None:
        return result
    try:
        saved = _save(client, actor, institution_id, row["user_id"], department)
    except Exception as exc:
        raise AppError(
            "The request was approved, but the department could not be saved. "
            "Set it from the roster.",
            500,
            "MEMBER_DEPARTMENT_NOT_SAVED",
        ) from exc
    return result.model_copy(update={"message": f"{result.message} {saved.message}"})


def with_departments(institution_id: UUID, roster: MembershipRoster) -> MembershipRoster:
    """Add each member's department to a roster from the same institution."""
    assignments = {
        str(row["user_id"]): row for row in repo.list_assignments(get_admin_client(), institution_id)
    }
    members = []
    for member in roster.members:
        row = assignments.get(str(member.user_id))
        department = (row or {}).get("departments") or {}
        members.append(
            member.model_copy(
                update={
                    "department_id": row.get("department_id") if row else None,
                    "department_code": department.get("code"),
                    "department_name": department.get("name"),
                }
            )
        )
    return roster.model_copy(update={"members": members})
