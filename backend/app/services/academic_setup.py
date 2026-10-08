"""Tenant-filtered reads and atomic, audited academic master writes."""

from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.core.security import authorize_permissions, has_permission, user_tenant_id
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all
from app.schemas.academic_setup import CREATE_MODELS, IDS

RESOURCES = {
    "departments": "departments", "programs": "departments",
    "academic_years": "academic_years", "semesters": "semesters",
    "courses": "courses", "program_courses": "courses",
    "course_offerings": "courses", "sections": "courses",
}
COLUMNS = {
    entity: ",".join([IDS[entity], *model.model_fields])
    for entity, model in CREATE_MODELS.items()
}


def tenant(user: dict) -> UUID:
    value = user_tenant_id(user)
    if value is None:
        raise AppError("Institution scope required", 403, "SCOPE_MISSING")
    return value


def catalogue(user: dict) -> dict:
    institution = tenant(user)
    readable = [entity for entity, resource in RESOURCES.items() if has_permission(user, f"{resource}.read")]
    if not readable:
        raise AppError("Academic setup permission required", 403, "FORBIDDEN")
    db = get_admin_client()

    def read(entity, column, values):
        if not values:
            return []
        result = []
        for offset in range(0, len(values), 100):
            query = db.table(entity).select(COLUMNS[entity]).order(IDS[entity])
            query = query.eq(column, str(institution)) if column == "institution_id" else query.in_(column, values[offset:offset + 100])
            result.extend(read_all(query))
        return result

    # Every query is pinned through a tenant-owned ancestor, including inactive
    # records needed for archive management. Never query all tenants then filter.
    rows = {}
    rows["departments"] = read("departments", "institution_id", [str(institution)])
    departments = [r["department_id"] for r in rows["departments"]]
    rows["programs"] = read("programs", "department_id", departments)
    rows["courses"] = read("courses", "department_id", departments)
    rows["academic_years"] = read("academic_years", "institution_id", [str(institution)])
    rows["semesters"] = read("semesters", "academic_year_id", [r["academic_year_id"] for r in rows["academic_years"]])
    programs = {r["program_id"] for r in rows["programs"]}
    courses = {r["course_id"] for r in rows["courses"]}
    years = {r["academic_year_id"] for r in rows["academic_years"]}
    semesters = {r["semester_id"]: r["academic_year_id"] for r in rows["semesters"]}
    rows["program_courses"] = [
        r for r in read("program_courses", "program_id", sorted(programs))
        if r["course_id"] in courses and (r.get("semester_id") is None or r["semester_id"] in semesters)
    ]
    rows["course_offerings"] = [
        r for r in read("course_offerings", "program_id", sorted(programs))
        if r["course_id"] in courses and r["academic_year_id"] in years
        and semesters.get(r["semester_id"]) == r["academic_year_id"]
    ]
    rows["sections"] = read("sections", "course_offering_id", [r["course_offering_id"] for r in rows["course_offerings"]])
    return {
        "institution_id": str(institution),
        "records": {entity: rows[entity] for entity in readable},
        "manageable": [entity for entity in readable if has_permission(user, f"{RESOURCES[entity]}.manage")],
    }


def save(user: dict, entity: str, payload: dict, record_id: UUID | None = None) -> dict:
    authorize_permissions(user, f"{RESOURCES[entity]}.manage")
    if not payload:
        raise AppError("At least one field is required", 422, "ACADEMIC_INPUT_INVALID")
    try:
        data = get_admin_client().rpc("manage_academic_master_record", {
            "p_actor_user_id": str(user["user_id"]), "p_institution_id": str(tenant(user)),
            "p_entity": entity, "p_record_id": str(record_id) if record_id else None,
            "p_payload": payload,
        }).execute().data
    except APIError as error:
        mapping = {
            "23505": (409, "ACADEMIC_DUPLICATE", "An academic record with this identifier or current status already exists."),
            "23P01": (409, "ACADEMIC_DATE_CONFLICT", "Active academic year dates overlap an existing year."),
            "23514": (422, "ACADEMIC_HIERARCHY_INVALID", "Check the academic hierarchy, active parents and date range."),
            "23503": (422, "ACADEMIC_REFERENCE_INVALID", "A required academic reference is unavailable."),
            "22023": (422, "ACADEMIC_INPUT_INVALID", "Invalid academic fields or an immutable relationship was changed."),
            "P0002": (404, "ACADEMIC_NOT_FOUND", "Academic record not found in your institution."),
            "42501": (403, "FORBIDDEN", "Academic management permission required."),
            "PGRST202": (503, "ACADEMIC_SCHEMA_UNAVAILABLE", "Academic setup requires the database update. Please contact your administrator."),
        }
        status, code, message = mapping.get(error.code, (500, "ACADEMIC_SAVE_FAILED", "Academic record could not be saved."))
        raise AppError(message, status, code) from error
    if not isinstance(data, dict):
        raise AppError("Invalid database projection", 500, "DATABASE_PROJECTION_INVALID")
    return data
