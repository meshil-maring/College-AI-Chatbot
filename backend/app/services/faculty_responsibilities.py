"""Faculty responsibilities extend the existing RBAC and teaching services."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.core.security import authorize_permissions, resolve_primary_role
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all as _all_rows, read_one
from app.schemas.faculty_responsibilities import AssignmentValidity, ResponsibilityCreate, ResponsibilityUpdate
from app.schemas.phase81 import FacultyAssignmentCreate
from app.services.authorization import assignment_is_active, effective_authorization
from app.services.phase81_rbac import _active_sections, list_institution_assignments, list_own_faculty_assignments


logger = logging.getLogger(__name__)


def _definitions() -> list[dict]:
    rows = _all_rows(get_admin_client().table("responsibility_definitions").select(
        "code, name, allowed_scope_types, exclusive_scope, responsibility_permissions(permissions(code, is_active))"
    ).eq("is_active", True).order("code"))
    return [{
        "code": row["code"], "name": row["name"],
        "allowed_scope_types": row["allowed_scope_types"], "exclusive_scope": row["exclusive_scope"],
        "permissions": sorted({mapping["permissions"]["code"] for mapping in row.get("responsibility_permissions", [])
                               if mapping.get("permissions") and mapping["permissions"].get("is_active")}),
    } for row in rows]


def _scope_options(institution_id: UUID) -> dict:
    db = get_admin_client()
    departments = _all_rows(db.table("departments").select("department_id, name, code").eq("institution_id", str(institution_id)).eq("is_active", True).order("department_id"))
    sections = _active_sections(institution_id)
    return {"departments": departments, "sections": sections}


def _live_scope(row: dict, options: dict) -> dict | None:
    """Re-derive the authoritative scope so changed/deactivated entities deny."""
    kind = row["scope_type"]
    if kind == "department":
        department = next((d for d in options["departments"] if str(d["department_id"]) == str(row["scope_id"])), None)
        return {"department_id": row["scope_id"], "scope_label": department["name"]} if department else None
    if kind == "section":
        section = next((s for s in options["sections"] if str(s["section_id"]) == str(row["scope_id"])), None)
        if section is None:
            return None
        keys = ("program_id", "academic_year_id", "semester_id", "section_code")
        if any(str(row.get(key)) != str(section[key]) for key in keys):
            return None
        return {**{key: section[key] for key in keys}, "section_id": section["section_id"],
                "scope_label": f'{section["program"]["name"]} · {section["semester"]["name"]} · Section {section["code"]} · {section["academic_year"]["name"]}'}
    # Future definitions use the same entities. Explicit composite semester
    # scope requires a program; it cannot widen to every program in that term.
    if kind == "institution":
        return {"scope_label": "Institution"} if str(row["scope_id"]) == str(row["institution_id"]) else None
    db = get_admin_client()
    table, key = {"program": ("programs", "program_id"), "course": ("courses", "course_id"), "semester": ("semesters", "semester_id")}.get(kind, (None, None))
    if table is None or key is None:
        return None
    entity = read_one(db.table(table).select("*").eq(key, str(row["scope_id"])).eq("is_active", True).maybe_single())
    if not entity:
        return None
    if kind == "semester":
        program = read_one(db.table("programs").select("program_id, department_id, name").eq("program_id", str(row.get("program_id"))).eq("is_active", True).maybe_single())
        if not program:
            return None
        entity = {**entity, "department_id": program["department_id"], "program_id": program["program_id"]}
        year = read_one(db.table("academic_years").select("academic_year_id").eq("academic_year_id", str(entity["academic_year_id"])).eq("institution_id", str(row["institution_id"])).eq("is_active", True).maybe_single())
        if not year:
            return None
    if not any(str(d["department_id"]) == str(entity.get("department_id")) for d in options["departments"]):
        return None
    expected = ("department_id", "program_id", "academic_year_id", "semester_id", "course_id")
    if any(row.get(key) is not None and str(row[key]) != str(entity.get(key)) for key in expected):
        return None
    return {"scope_label": entity["name"]}


def list_responsibilities(institution_id: UUID, faculty_user_id: UUID | None = None, *, active_only: bool = False) -> list[dict]:
    query = get_admin_client().table("faculty_responsibilities").select("*").eq("institution_id", str(institution_id)).order("created_at")
    if faculty_user_id is not None:
        query = query.eq("faculty_user_id", str(faculty_user_id))
    definitions = {row["code"]: row for row in _definitions()}
    options = _scope_options(institution_id)
    result = []
    for row in _all_rows(query):
        definition = definitions.get(row["responsibility_code"])
        scope = _live_scope(row, options) if definition else None
        live = bool(definition and scope and row["scope_type"] in definition["allowed_scope_types"] and assignment_is_active(row))
        if active_only and not live:
            continue
        result.append({**row, **(scope or {}), "name": definition["name"] if definition else row["responsibility_code"],
                       "permissions": definition["permissions"] if definition and live else [], "effective_active": live,
                       "state": _assignment_state(row, live)})
    return result


def _assignment_state(row: dict, live: bool) -> str:
    if row.get("revoked_at"):
        return "revoked"
    if not row["is_active"]:
        return "inactive"
    if live:
        return "active"
    now = datetime.now(timezone.utc)
    try:
        start = datetime.fromisoformat(str(row["start_at"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(row["end_at"]).replace("Z", "+00:00")) if row.get("end_at") else None
        if start > now:
            return "scheduled"
        if end is not None and now >= end:
            return "expired"
    except (ValueError, TypeError):
        pass
    return "scope unavailable"


def faculty_context(current_user: dict) -> dict:
    if current_user.get("status") != "active" or resolve_primary_role(current_user.get("roles")) != "faculty" or not current_user.get("institution_id"):
        raise AppError("Active Faculty context required", 403, "FORBIDDEN")
    if not any(g.get("role") == "faculty" and g.get("is_active", True) and g.get("scope_type") == "institution"
               and str(g.get("scope_id")) == str(current_user["institution_id"]) for g in current_user.get("role_assignments", [])):
        raise AppError("Faculty institution grant required", 403, "FORBIDDEN")
    tenant = UUID(str(current_user["institution_id"]))
    try:
        responsibilities = list_responsibilities(tenant, UUID(str(current_user["user_id"])), active_only=True)
        teaching = list_own_faculty_assignments(current_user)
    except APIError as error:
        # A deployment can authenticate against the existing identity tables
        # before the faculty migrations have been applied. Only recognize
        # missing faculty schema; other database errors still propagate.
        faculty_tables = (
            "responsibility_definitions", "responsibility_permissions",
            "faculty_responsibilities", "faculty_section_assignments",
        )
        if error.code not in {"PGRST200", "PGRST204", "PGRST205", "42P01", "42703"} or not any(
            table in error.message for table in faculty_tables
        ):
            raise
        logger.warning(
            "event=faculty_schema_unavailable database_code=%s "
            "required_migration=20261011000000_faculty_responsibilities_and_validity.sql",
            error.code,
        )
        raise AppError(
            "Faculty assignments and responsibilities are temporarily unavailable. Please contact your administrator.",
            503,
            "FACULTY_SCHEMA_UNAVAILABLE",
        ) from error
    return {"responsibilities": responsibilities, "teaching_assignments": teaching,
            "responsibility_permissions": sorted({code for row in responsibilities for code in row["permissions"]})}


def authorize_section(current_user: dict, section_id: UUID, permission: str, *, teaching_only: bool = False, owner_user_id: str | None = None, require_owner: bool = False) -> dict:
    tenant = current_user.get("institution_id")
    if not tenant:
        raise AppError("Institution scope required", 403, "FACULTY_SCOPE_DENIED")
    sections = _active_sections(UUID(str(tenant)))
    resource = next((s for s in sections if str(s["section_id"]) == str(section_id)), None)
    if resource is None:
        raise AppError("Section is outside your active academic scope", 403, "FACULTY_SCOPE_DENIED")
    teaching = _all_rows(get_admin_client().table("faculty_section_assignments").select("*").eq("institution_id", str(tenant)).eq("faculty_user_id", str(current_user["user_id"])).eq("section_id", str(section_id)))
    responsibilities = [] if teaching_only else list_responsibilities(UUID(str(tenant)), UUID(str(current_user["user_id"])), active_only=True)
    if not effective_authorization(current_user, resource, permission, teaching=teaching, responsibilities=responsibilities,
                                   owner_user_id=owner_user_id, require_owner=require_owner):
        raise AppError("You do not have an active assignment for this action", 403, "FACULTY_SCOPE_DENIED")
    return resource


def management_data(current_user: dict, institution_id: UUID) -> dict:
    _assert_manager(current_user, institution_id)
    return {**list_institution_assignments(institution_id), **_scope_options(institution_id),
            "definitions": _definitions(), "responsibilities": list_responsibilities(institution_id)}


def _assert_manager(actor: dict, institution_id: UUID) -> None:
    authorize_permissions(actor, "faculty.assignments.manage")
    if actor.get("status") != "active":
        raise AppError("Active account required", 403, "ACCOUNT_INACTIVE")
    grants = actor.get("role_assignments", [])
    if not any(g.get("is_active", True) and g.get("role") in actor.get("roles", []) and (
        (g.get("role") == "admin" and g.get("scope_type") == "institution" and str(g.get("scope_id")) == str(institution_id))
        or (g.get("role") == "super_admin" and g.get("scope_type") == "platform" and g.get("scope_id") is None)
    ) for g in grants):
        raise AppError("Assignment management scope denied", 403, "FORBIDDEN")


def _rpc(name: str, fields: dict, *, client=None) -> dict:
    try:
        db = client if client is not None else get_admin_client()
        value = db.rpc(name, fields).execute().data
    except APIError as error:
        code = error.code
        if code == "23P01":
            raise AppError("This responsibility overlaps an existing appointment", 409, "ASSIGNMENT_CONFLICT") from error
        if code == "P0002":
            raise AppError("Assignment not found", 404, "ASSIGNMENT_NOT_FOUND") from error
        if code in {"23514", "23503", "23505"}:
            raise AppError("Invalid faculty, responsibility, scope, or validity", 422, "INVALID_ASSIGNMENT") from error
        if code == "42501":
            raise AppError("Assignment authority denied", 403, "FORBIDDEN") from error
        raise
    return {"responsibility_id" if name == "manage_faculty_responsibility" else "assignment_id": str(value) if value is not None else None}


def change_responsibility(actor: dict, institution_id: UUID, payload: ResponsibilityCreate | ResponsibilityUpdate | None, *, responsibility_id: UUID | None = None, revoke: bool = False) -> dict:
    _assert_manager(actor, institution_id)
    row = None
    if responsibility_id:
        row = read_one(get_admin_client().table("faculty_responsibilities").select("*").eq("institution_id", str(institution_id)).eq("responsibility_id", str(responsibility_id)).maybe_single())
        if not row:
            raise AppError("Responsibility not found", 404, "ASSIGNMENT_NOT_FOUND")
    values = payload.model_dump(mode="json") if payload else (row or {})
    target = str(row["faculty_user_id"] if row else values["faculty_user_id"])
    if target == str(actor["user_id"]):
        raise AppError("You cannot assign yourself responsibilities", 403, "SELF_ASSIGNMENT_DENIED")
    return _rpc("manage_faculty_responsibility", {
        "p_actor_user_id": str(actor["user_id"]), "p_institution_id": str(institution_id),
        "p_faculty_user_id": target, "p_responsibility_code": row["responsibility_code"] if row else values["responsibility_code"],
        "p_scope_type": values["scope_type"], "p_scope_id": str(values["scope_id"]),
        "p_program_id": str(values["program_id"]) if values.get("program_id") else None,
        "p_start_at": values["start_at"], "p_end_at": values.get("end_at"), "p_is_active": values["is_active"],
        "p_responsibility_id": str(responsibility_id) if responsibility_id else None, "p_revoke": revoke,
    })


def update_teaching(actor: dict, institution_id: UUID, assignment_id: UUID, payload: AssignmentValidity) -> dict:
    _assert_manager(actor, institution_id)
    return _rpc("update_faculty_teaching_validity", {
        "p_actor_user_id": str(actor["user_id"]), "p_institution_id": str(institution_id), "p_assignment_id": str(assignment_id),
        "p_start_at": payload.start_at.isoformat(), "p_end_at": payload.end_at.isoformat() if payload.end_at else None,
        "p_is_active": payload.is_active,
    })


def create_teaching(actor: dict, institution_id: UUID, payload: FacultyAssignmentCreate) -> dict:
    _assert_manager(actor, institution_id)
    if str(actor["user_id"]) == str(payload.faculty_user_id):
        raise AppError("You cannot assign yourself teaching duties", 403, "SELF_ASSIGNMENT_DENIED")
    if payload.start_at is None:
        raise AppError("Teaching validity is required", 422, "INVALID_ASSIGNMENT")
    return _rpc("create_faculty_teaching_assignment", {
        "p_actor_user_id": str(actor["user_id"]), "p_institution_id": str(institution_id),
        "p_faculty_user_id": str(payload.faculty_user_id), "p_section_id": str(payload.section_id),
        "p_start_at": payload.start_at.isoformat(), "p_end_at": payload.end_at.isoformat() if payload.end_at else None,
        "p_is_active": payload.is_active,
    })


def responsibility_report(current_user: dict, responsibility_id: UUID) -> dict:
    context = faculty_context(current_user)
    appointment = next((row for row in context["responsibilities"] if str(row["responsibility_id"]) == str(responsibility_id)), None)
    if appointment is None:
        raise AppError("Active responsibility not found", 403, "FACULTY_SCOPE_DENIED")
    if not all(permission in appointment["permissions"] for permission in ("academic.reports.read", "students.read", "attendance.overview.read")):
        raise AppError("Academic reporting permission denied", 403, "FORBIDDEN")
    sections = [s for s in _active_sections(UUID(str(current_user["institution_id"]))) if all(
        effective_authorization(current_user, s, permission, teaching=[], responsibilities=[appointment])
        for permission in ("academic.reports.read", "students.read", "attendance.overview.read")
    )]
    section_ids = [s["section_id"] for s in sections]
    db = get_admin_client()
    roster = _all_rows(db.table("faculty_attendance_rosters").select("roster_id, section_id, register_number, student_name, roster_status").eq("institution_id", str(current_user["institution_id"])).in_("section_id", section_ids).order("roster_id")) if section_ids else []
    sessions = _all_rows(db.table("faculty_attendance_sessions").select("session_id, section_id").eq("institution_id", str(current_user["institution_id"])).in_("section_id", section_ids).order("session_id")) if section_ids else []
    by_roster = {r["roster_id"]: {**r, "total_classes": 0, "present_classes": 0, "attendance_percentage": None} for r in roster}
    # Query in bounded batches; reports derive percentages from session records,
    # never imported percentage summaries or inferred student enrollments.
    session_ids = [s["session_id"] for s in sessions]
    for offset in range(0, len(session_ids), 100):
        for record in _all_rows(db.table("faculty_attendance_records").select("record_id, roster_id, status").in_("session_id", session_ids[offset:offset + 100]).order("record_id")):
            if record["roster_id"] in by_roster:
                student = by_roster[record["roster_id"]]
                student["total_classes"] += 1
                student["present_classes"] += int(record["status"] == "present")
    students = list(by_roster.values())
    for student in students:
        if student["total_classes"]:
            student["attendance_percentage"] = round(100 * student["present_classes"] / student["total_classes"], 2)
    faculty = []
    if section_ids and any(effective_authorization(current_user, s, "faculty.read", teaching=[], responsibilities=[appointment]) for s in sections):
        assignments = _all_rows(db.table("faculty_section_assignments").select("*").eq("institution_id", str(current_user["institution_id"])).in_("section_id", section_ids).order("assignment_id"))
        faculty_ids = sorted({a["faculty_user_id"] for a in assignments if assignment_is_active(a)})
        if faculty_ids:
            eligible = _all_rows(db.table("user_roles").select("user_id, roles!inner(name, is_active)").in_("user_id", faculty_ids).eq("scope_type", "institution").eq("scope_id", str(current_user["institution_id"])).eq("roles.name", "faculty").eq("roles.is_active", True).order("user_id"))
            eligible_ids = [r["user_id"] for r in eligible]
            if eligible_ids:
                faculty = _all_rows(db.table("users").select("id, first_name, last_name").in_("id", eligible_ids).eq("status", "active").order("id"))
    return {"responsibility": appointment, "sections": sections, "students": students,
            "low_attendance": [s for s in students if s["attendance_percentage"] is not None and s["attendance_percentage"] < 75],
            "low_attendance_threshold": 75, "faculty": faculty, "session_count": len(sessions)}
