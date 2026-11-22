"""Staff/Faculty employee profiles and additional departments.

The administrator completes or edits a member's employee profile: the common
fields shared by every member type and the Faculty or Staff details of the
member's role. A member keeps one primary department (``member_departments``)
and may have up to ten additional departments. Department association does not
grant teaching access; teaching assignments are configured separately.

Every write is a tenant-checked, audited database command. Employment status is
derived from the contract end date rather than stored.
"""

from datetime import date
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_memberships as membership_repo
from app.repositories.admin import member_departments as department_repo
from app.repositories.admin import member_profiles as repo
from app.schemas.admin.admin_memberships import MembershipRoster
from app.schemas.admin.member_profiles import (
    CommonProfile,
    DepartmentRef,
    FacultyProfile,
    MemberAdditionalDepartmentsResult,
    MemberAdditionalDepartmentsWrite,
    MemberProfileSaved,
    MemberProfileView,
    MemberProfileWrite,
    StaffProfile,
)

DATABASE_ERRORS = {
    "P1201": (422, "DEPARTMENT_INVALID", "Choose active departments of your institution."),
    "P1204": (409, "EMPLOYEE_ID_IN_USE", "This employee ID is already used in your institution."),
    "P1205": (404, "MEMBER_NOT_FOUND", "Staff or faculty member not found"),
    "22023": (422, "PROFILE_INVALID", "Check the profile details, then try again."),
    "23514": (422, "PROFILE_INVALID", "Check the profile details, then try again."),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action."),
}


def _database_call(call, failure: str):
    try:
        return call()
    except AppError:
        raise
    except Exception as exc:
        mapped = DATABASE_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise AppError(failure, 502, "MEMBER_PROFILE_WRITE_FAILED") from exc


def _member_role(client, institution_id: UUID, user_id: UUID) -> str:
    """Faculty or Staff role held in this institution (Faculty wins), else 404."""
    roles = {
        (grant.get("roles") or {}).get("name")
        for grant in membership_repo.list_user_grants(client, user_id)
        if grant.get("scope_type") == "institution" and str(grant.get("scope_id")) == str(institution_id)
    }
    for role in ("faculty", "staff"):
        if role in roles:
            return role
    raise AppError("Staff or faculty member not found", 404, "MEMBER_NOT_FOUND")


def _ref(row: dict[str, Any]) -> DepartmentRef:
    department = row.get("departments") or {}
    return DepartmentRef(
        department_id=row["department_id"],
        code=str(department.get("code") or ""),
        name=str(department.get("name") or ""),
    )


def _employment_status(detail: FacultyProfile | StaffProfile | None) -> str:
    if detail is None:
        return "not_set"
    end = detail.contract_end_date
    return "contract_ended" if end is not None and end < date.today() else "active"


def _roster_employment_status(row: dict[str, Any] | None) -> str:
    if not row:
        return "not_set"
    end = row.get("contract_end_date")
    return "contract_ended" if end and date.fromisoformat(str(end)[:10]) < date.today() else "active"


def get_profile(institution_id: UUID, user_id: UUID) -> MemberProfileView:
    client = get_admin_client()
    role = _member_role(client, institution_id, user_id)
    common = repo.list_common(client, institution_id, user_id)
    rows = (repo.list_faculty if role == "faculty" else repo.list_staff)(client, institution_id, user_id)
    model = FacultyProfile if role == "faculty" else StaffProfile
    detail = model.model_validate({k: v for k, v in rows[0].items() if k != "user_id"}) if rows else None
    primary = [
        row for row in department_repo.list_assignments(client, institution_id)
        if str(row.get("user_id")) == str(user_id)
    ]
    return MemberProfileView(
        user_id=user_id,
        role=role,
        common=CommonProfile.model_validate({k: v for k, v in common[0].items() if k != "user_id"})
        if common else None,
        faculty=detail if role == "faculty" else None,
        staff=detail if role == "staff" else None,
        employment_status=_employment_status(detail),
        primary_department=_ref(primary[0]) if primary else None,
        additional_departments=[_ref(row) for row in repo.list_additional(client, institution_id, user_id)],
    )


def save_profile(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID, body: MemberProfileWrite
) -> MemberProfileSaved:
    client = get_admin_client()
    role = _member_role(client, institution_id, user_id)
    if body.role != role:
        raise AppError(
            f"This member is {role.title()}; enter the {role} details", 422, "PROFILE_ROLE_MISMATCH"
        )
    _database_call(
        lambda: repo.save_profile(
            client, actor_id=actor["user_id"], institution_id=institution_id,
            user_id=user_id, profile=body.database_payload(),
        ),
        "The profile could not be saved. Try again.",
    )
    return MemberProfileSaved(user_id=user_id, role=role, message="Employee profile saved.")


def set_additional_departments(
    actor: dict[str, Any], institution_id: UUID, user_id: UUID, body: MemberAdditionalDepartmentsWrite
) -> MemberAdditionalDepartmentsResult:
    client = get_admin_client()
    _database_call(
        lambda: repo.set_additional_departments(
            client, actor_id=actor["user_id"], institution_id=institution_id,
            user_id=user_id, department_ids=list(dict.fromkeys(body.department_ids)),
        ),
        "The departments could not be saved. Try again.",
    )
    departments = [_ref(row) for row in repo.list_additional(client, institution_id, user_id)]
    return MemberAdditionalDepartmentsResult(
        user_id=user_id,
        additional_departments=departments,
        message="Additional departments saved." if departments else "Additional departments cleared.",
    )


def with_profiles(institution_id: UUID, roster: MembershipRoster) -> MembershipRoster:
    """Add each member's employee ID, designation, employment type and extra departments."""
    client = get_admin_client()
    common = {str(row["user_id"]): row for row in repo.list_common(client, institution_id)}
    # A member whose role changed keeps the old role's row; show the current role's.
    employment = {
        role: {str(row["user_id"]): row for row in rows}
        for role, rows in (("staff", repo.list_staff(client, institution_id)),
                           ("faculty", repo.list_faculty(client, institution_id)))
    }
    additional: dict[str, list[str]] = {}
    for row in repo.list_additional(client, institution_id):
        additional.setdefault(str(row["user_id"]), []).append(_ref(row).name)
    members = []
    for member in roster.members:
        key = str(member.user_id)
        profile = common.get(key) or {}
        members.append(member.model_copy(update={
            "employee_id": profile.get("employee_id"),
            "designation": profile.get("designation"),
            "employment_type": (employment.get(member.role, {}).get(key) or {}).get("employment_type"),
            "employment_status": _roster_employment_status(employment.get(member.role, {}).get(key)),
            "additional_department_names": sorted(additional.get(key, [])),
        }))
    return roster.model_copy(update={"members": members})
