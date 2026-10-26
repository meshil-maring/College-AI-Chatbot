"""Read the exported academic model through tenant-scoped relationship joins."""

from app.repositories.shared.query_pages import read_all, read_one
from app.schemas.academics.academic_setup import AcademicEntity as Entity


PRIMARY_KEYS = {entity: entity.value.removesuffix("s") + "_id" for entity in Entity}
PRIMARY_KEYS[Entity.academic_years] = "academic_year_id"
TABLES = {entity: entity.value for entity in Entity}
FIELDS = {
    Entity.departments: "department_id,institution_id,name,code,description,is_active",
    Entity.programs: "program_id,department_id,name,code,description,degree_type,duration_years,total_credits,is_active",
    Entity.academic_years: "academic_year_id,institution_id,name,code,start_date,end_date,is_current,is_active",
    Entity.semesters: "semester_id,academic_year_id,name,code,semester_number,start_date,end_date,is_current,is_active",
    Entity.courses: "course_id,department_id,name,code,description,credits,lecture_hours,tutorial_hours,practical_hours,is_active",
    Entity.program_courses: "program_course_id,program_id,course_id,semester_id,course_type,is_required,is_active",
    Entity.course_offerings: "course_offering_id,course_id,program_id,academic_year_id,semester_id,capacity,is_active",
    Entity.sections: "section_id,course_offering_id,name,code,capacity,is_active",
}
DEPARTMENT = "department:departments!inner(institution_id)"
PROGRAM = f"program:programs!inner({DEPARTMENT})"
COURSE = f"course:courses!inner({DEPARTMENT})"
YEAR = "year:academic_years!inner(institution_id)"
JOINS = {
    Entity.departments: ("", ("institution_id",)),
    Entity.academic_years: ("", ("institution_id",)),
    Entity.programs: (DEPARTMENT, ("department.institution_id",)),
    Entity.courses: (DEPARTMENT, ("department.institution_id",)),
    Entity.semesters: (YEAR, ("year.institution_id",)),
    Entity.program_courses: (f"{PROGRAM},{COURSE}", ("program.department.institution_id", "course.department.institution_id")),
    Entity.course_offerings: (f"{PROGRAM},{COURSE},{YEAR}", ("program.department.institution_id", "course.department.institution_id", "year.institution_id")),
    Entity.sections: (
        f"offering:course_offerings!inner({PROGRAM},{COURSE},{YEAR})",
        ("offering.program.department.institution_id", "offering.course.department.institution_id", "offering.year.institution_id"),
    ),
}
PROJECTIONS = {entity: ",".join(part for part in (FIELDS[entity], JOINS[entity][0]) if part) for entity in Entity}


def get_institution_lifecycle(client, institution_id):
    return read_one(client.table("institutions").select("institution_id,organization_id,status,is_active")
                    .eq("institution_id", institution_id).maybe_single())


def get_organization_lifecycle(client, organization_id):
    return read_one(client.table("organizations").select("organization_id,status")
                    .eq("organization_id", organization_id).maybe_single())


def _query(client, institution_id, entity):
    query = client.table(TABLES[entity]).select(PROJECTIONS[entity])
    for path in JOINS[entity][1]:
        query = query.eq(path, institution_id)
    return query


def _project(row, institution_id):
    # institution_id is an API envelope derived from the scoped join, not a
    # physical column on descendants. Embedded join data stays in the repository.
    return {key: value for key, value in row.items() if key not in {"department", "program", "course", "year", "offering"}} | {"institution_id": institution_id}


def list_records(client, institution_id, entity):
    query = _query(client, institution_id, entity)
    if entity not in {Entity.program_courses, Entity.course_offerings}:
        query = query.order("name")
    rows = read_all(query.order(PRIMARY_KEYS[entity]))
    return [_project(row, institution_id) for row in rows]


def get_record(client, institution_id, entity, record_id):
    row = read_one(_query(client, institution_id, entity).eq(PRIMARY_KEYS[entity], record_id).maybe_single())
    return _project(row, institution_id) if row else None


def manage_record(client, actor_id, institution_id, entity, record_id, payload):
    return client.rpc("manage_academic_master_record", {
        "p_actor_user_id": actor_id, "p_institution_id": institution_id,
        "p_entity": entity.value, "p_record_id": record_id, "p_payload": payload,
    }).execute().data
