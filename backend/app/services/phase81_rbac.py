"""Phase 8.1 tenant-scoped Staff grants and Faculty section assignments."""

from collections.abc import Iterable
from uuid import UUID

from app.core.errors import AppError
from app.core.permissions import DELEGABLE_STAFF_PERMISSIONS
from app.db.supabase import get_admin_client
from app.services import admin_memberships
from app.services.authorization import assignment_is_active
from app.services.faculty_schema import faculty_schema_required
from app.repositories.query_pages import read_all, read_one, read_rows


def _active_sections(institution_id: UUID) -> list[dict]:
    client = get_admin_client()
    departments = read_all(
        client.table("departments")
        .select("department_id, name, code")
        .eq("institution_id", str(institution_id))
        .eq("is_active", True)
        .order("department_id")
    )
    department_ids = [row["department_id"] for row in departments]
    if not department_ids:
        return []
    courses = read_all(
        client.table("courses")
        .select("course_id, name, code, department_id")
        .in_("department_id", department_ids)
        .eq("is_active", True)
        .order("course_id")
    )
    course_ids = [row["course_id"] for row in courses]
    if not course_ids:
        return []
    offerings = read_all(
        client.table("course_offerings")
        .select("course_offering_id, course_id, academic_year_id, semester_id, program_id")
        .in_("course_id", course_ids)
        .eq("is_active", True)
        .order("course_offering_id")
    )
    offering_ids = [row["course_offering_id"] for row in offerings]
    if not offering_ids:
        return []
    program_ids = sorted({str(row["program_id"]) for row in offerings if row.get("program_id")})
    if not program_ids:
        return []
    sections = read_all(
        client.table("sections")
        .select("section_id, course_offering_id, name, code, capacity")
        .in_("course_offering_id", offering_ids)
        .eq("is_active", True)
        .order("section_id")
    )
    courses_by_id = {str(row["course_id"]): row for row in courses}
    departments_by_id = {str(row["department_id"]): row for row in departments}
    offerings_by_id = {str(row["course_offering_id"]): row for row in offerings}
    programs = {str(row["program_id"]): row for row in read_all(client.table("programs").select("program_id, name, code, department_id").in_("program_id", program_ids).eq("is_active", True).order("program_id"))}
    semesters = {str(row["semester_id"]): row for row in read_all(client.table("semesters").select("semester_id, name, academic_year_id, semester_number").eq("is_active", True).order("semester_id"))}
    years = {str(row["academic_year_id"]): row for row in read_all(client.table("academic_years").select("academic_year_id, name").eq("institution_id", str(institution_id)).eq("is_active", True).order("academic_year_id"))}
    rows = []
    for section in sections:
        offering = offerings_by_id.get(str(section["course_offering_id"]))
        course = courses_by_id.get(str(offering["course_id"])) if offering else None
        if offering is None or course is None:
            continue
        program = programs.get(str(offering.get("program_id")))
        semester = semesters.get(str(offering.get("semester_id")))
        year = years.get(str(offering.get("academic_year_id")))
        if (program is None or semester is None or year is None
                or str(semester["academic_year_id"]) != str(offering["academic_year_id"])):
            continue
        rows.append({
            **section,
            "course": {"course_id": course["course_id"], "name": course["name"], "code": course["code"]},
            "academic_year_id": offering["academic_year_id"],
            "semester_id": offering["semester_id"],
            "program_id": offering["program_id"],
            "department_id": course["department_id"],
            "department": departments_by_id[str(course["department_id"])],
            "institution_id": str(institution_id),
            "course_id": course["course_id"],
            "section_code": section["code"],
            "program": program,
            "semester": semester,
            "academic_year": year,
        })
    return rows


def _staff_member(user_id: UUID, institution_id: UUID) -> dict:
    result = read_one(
        get_admin_client()
        .table("users")
        .select(
            "id, status, email, first_name, last_name, "
            "user_roles!inner(scope_type, scope_id, roles!inner(name, is_active))"
        )
        .eq("id", str(user_id))
        .eq("status", "active")
        .eq("user_roles.scope_type", "institution")
        .eq("user_roles.scope_id", str(institution_id))
        .eq("user_roles.roles.name", "staff")
        .eq("user_roles.roles.is_active", True)
        .maybe_single()
    )
    if result is None:
        raise AppError("Active Staff member not found", 404, "STAFF_MEMBER_NOT_FOUND")
    return result


def list_delegable_permissions() -> list[str]:
    client = get_admin_client()
    rows = read_rows(
        client.table("permissions")
        .select("code")
        .in_("code", sorted(DELEGABLE_STAFF_PERMISSIONS))
        .eq("is_active", True)
        .order("code")
    )
    active_codes = {row["code"] for row in rows}
    return sorted(active_codes & DELEGABLE_STAFF_PERMISSIONS)


def list_staff_permissions(user_id: UUID, institution_id: UUID) -> dict:
    _staff_member(user_id, institution_id)
    client = get_admin_client()
    grants = read_rows(
        client.table("user_roles")
        .select(
            "scope_type, scope_id, roles(name, is_active, "
            "role_permissions(permissions(code, is_active)))"
        )
        .eq("user_id", str(user_id))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
    )
    inherited: set[str] = set()
    for grant in grants:
        role = grant.get("roles")
        if not isinstance(role, dict) or not role.get("is_active", True):
            continue
        for role_permission in role.get("role_permissions") or []:
            permission = role_permission.get("permissions")
            if isinstance(permission, dict) and permission.get("is_active", True):
                code = permission.get("code")
                if isinstance(code, str):
                    inherited.add(code)

    direct_rows = read_rows(
        client.table("user_permission_grants")
        .select("grant_id, granted_at, permissions(code, is_active)")
        .eq("user_id", str(user_id))
        .eq("institution_id", str(institution_id))
        .is_("revoked_at", "null")
        .order("granted_at")
    )
    direct = {
        permission["code"]: str(row["grant_id"])
        for row in direct_rows
        if isinstance((permission := row.get("permissions")), dict)
        and permission.get("is_active", True)
        and isinstance(permission.get("code"), str)
    }
    return {
        "user_id": str(user_id),
        "institution_id": str(institution_id),
        "permissions": [
            {
                "code": code,
                "inherited": code in inherited,
                "direct_grant_id": direct.get(code),
            }
            for code in sorted(inherited | set(direct))
        ],
        "delegable_permissions": list_delegable_permissions(),
    }


def change_staff_permissions(
    actor: dict,
    institution_id: UUID,
    target_user_id: UUID,
    permission_codes: Iterable[str],
    *,
    grant: bool,
) -> dict:
    codes = list(permission_codes)
    if len(codes) != len(set(codes)):
        raise AppError("Duplicate permission codes are not allowed", 422, "DUPLICATE_PERMISSION")
    unknown = set(codes) - DELEGABLE_STAFF_PERMISSIONS
    if unknown:
        raise AppError(
            "One or more permissions are not delegable to Staff",
            422,
            "PERMISSION_NOT_DELEGABLE",
        )
    _staff_member(target_user_id, institution_id)
    response = (
        get_admin_client()
        .rpc(
            "phase81_manage_staff_permission_grants",
            {
                "p_actor_user_id": str(actor["user_id"]),
                "p_institution_id": str(institution_id),
                "p_target_user_id": str(target_user_id),
                "p_permission_codes": codes,
                "p_grant": grant,
            },
        )
        .execute()
    )
    changed = response.data
    if not isinstance(changed, int):
        raise AppError("Invalid permission mutation result", 500, "DATABASE_PROJECTION_INVALID")
    return {
        "changed": changed,
        "permissions": list_staff_permissions(target_user_id, institution_id),
    }


@faculty_schema_required
def list_institution_assignments(institution_id: UUID) -> dict:
    client = get_admin_client()
    faculty_roster = admin_memberships.list_roster(
        institution_id, role="faculty", status="active"
    )
    faculty_candidates = [
        {
            "id": str(member.user_id),
            "email": member.email,
            "first_name": member.name,
            "last_name": "",
        }
        for member in faculty_roster.members
        if member.user_id is not None
    ]
    assignments = read_all(
        client.table("faculty_section_assignments")
        .select("assignment_id, faculty_user_id, section_id, assigned_at, start_at, end_at, is_active, revoked_at")
        .eq("institution_id", str(institution_id))
        .is_("revoked_at", "null")
        .order("assigned_at", desc=True)
    )
    sections = _active_sections(institution_id)
    active_section_ids = {str(section["section_id"]) for section in sections}
    assignments = [
        row for row in assignments if str(row["section_id"]) in active_section_ids
    ]
    faculty_ids = sorted({row["faculty_user_id"] for row in assignments})
    faculty_rows = (
        read_all(
            client.table("users")
            .select("id, email, first_name, last_name, status")
            .in_("id", faculty_ids)
            .eq("status", "active")
            .order("id")
        )
        if faculty_ids
        else []
    )
    active_roles = (
        read_all(
            client.table("user_roles")
            .select("user_id, roles!inner(name, is_active)")
            .in_("user_id", faculty_ids)
            .eq("scope_type", "institution")
            .eq("scope_id", str(institution_id))
            .eq("roles.name", "faculty")
            .eq("roles.is_active", True)
            .order("user_id")
        )
        if faculty_ids
        else []
    )
    eligible_faculty_ids = {str(row["user_id"]) for row in active_roles}
    faculty_rows = [
        row for row in faculty_rows if str(row["id"]) in eligible_faculty_ids
    ]
    faculty_by_id = {str(row["id"]): row for row in faculty_rows}
    sections_by_id = {str(row["section_id"]): row for row in sections}
    return {
        "sections": sections,
        "faculty": faculty_candidates,
        "assignments": [
            {
                **row,
                "faculty": faculty_by_id.get(str(row["faculty_user_id"])),
                "section": sections_by_id.get(str(row["section_id"])),
            }
            for row in assignments
            if str(row["faculty_user_id"]) in faculty_by_id
        ],
    }


@faculty_schema_required
def list_own_faculty_assignments(current_user: dict) -> list[dict]:
    institution_id = UUID(str(current_user["institution_id"]))
    sections = {str(row["section_id"]): row for row in _active_sections(institution_id)}
    rows = read_all(
        get_admin_client()
        .table("faculty_section_assignments")
        .select("assignment_id, faculty_user_id, institution_id, section_id, assigned_at, start_at, end_at, is_active, revoked_at")
        .eq("institution_id", str(institution_id))
        .eq("faculty_user_id", str(current_user["user_id"]))
        .is_("revoked_at", "null")
        .order("assigned_at", desc=True)
    )
    return [
        {**row, "section": sections[str(row["section_id"])]}
        for row in rows
        if str(row["section_id"]) in sections and assignment_is_active(row)
    ]


def manage_faculty_assignment(
    actor: dict,
    institution_id: UUID,
    faculty_user_id: UUID,
    section_id: UUID,
    *,
    revoke: bool,
) -> dict:
    from app.services.faculty_responsibilities import _rpc
    response = _rpc(
        "phase81_manage_faculty_section_assignment",
        {
            "p_actor_user_id": str(actor["user_id"]),
            "p_institution_id": str(institution_id),
            "p_faculty_user_id": str(faculty_user_id),
            "p_section_id": str(section_id),
            "p_revoke": revoke,
        },
        client=get_admin_client(),
    )
    result = response["assignment_id"]
    if revoke and result is None:
        raise AppError("Faculty assignment not found", 404, "FACULTY_ASSIGNMENT_NOT_FOUND")
    return {"assignment_id": str(result) if result is not None else None}


@faculty_schema_required
def revoke_faculty_assignment(
    actor: dict, institution_id: UUID, assignment_id: UUID
) -> dict:
    assignment = read_one(
        get_admin_client()
        .table("faculty_section_assignments")
        .select("faculty_user_id, section_id")
        .eq("assignment_id", str(assignment_id))
        .eq("institution_id", str(institution_id))
        .is_("revoked_at", "null")
        .maybe_single()
    )
    if assignment is None:
        raise AppError("Faculty assignment not found", 404, "FACULTY_ASSIGNMENT_NOT_FOUND")
    return manage_faculty_assignment(
        actor,
        institution_id,
        UUID(str(assignment["faculty_user_id"])),
        UUID(str(assignment["section_id"])),
        revoke=True,
    )
