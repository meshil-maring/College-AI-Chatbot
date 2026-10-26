"""Validate the export's active ancestry and matching program-course links."""

from app.core.errors import AppError
from app.repositories.academics import academic_setup as repository
from app.schemas.academics.academic_setup import AcademicEntity as Entity


def active_parent(client, institution_id, entity, record_id, label):
    parent = repository.get_record(client, institution_id, entity, str(record_id))
    if parent is None or parent.get("is_active") is not True:
        raise AppError(f"Choose an active {label}", 422, "ACADEMIC_REFERENCE_INVALID")
    return parent


def validate_structure_parents(client, institution_id, entity, fields, existing):
    values = {**(existing or {}), **fields}
    check_active = existing is None or fields.get("is_active") is True
    # Semester dates must fit the parent year even for a metadata/date repair.
    if entity == Entity.semesters:
        year = repository.get_record(client, institution_id, Entity.academic_years, values["academic_year_id"])
        if not year or values["start_date"] < year["start_date"] or values["end_date"] > year["end_date"]:
            raise AppError("Semester dates must fit its academic year", 422, "ACADEMIC_REFERENCE_INVALID")
    if not check_active:
        return

    def parent(kind, key, label):
        return active_parent(client, institution_id, kind, values[key], label)

    if entity in {Entity.programs, Entity.courses}:
        parent(Entity.departments, "department_id", "department")
    elif entity == Entity.semesters:
        parent(Entity.academic_years, "academic_year_id", "academic year")
    elif entity in {Entity.program_courses, Entity.course_offerings}:
        program = parent(Entity.programs, "program_id", "program")
        course = parent(Entity.courses, "course_id", "course")
        for owner in (program, course):
            active_parent(client, institution_id, Entity.departments, owner["department_id"], "department")
        if values.get("semester_id"):
            semester = parent(Entity.semesters, "semester_id", "semester")
            active_parent(client, institution_id, Entity.academic_years, semester["academic_year_id"], "academic year")
            if entity == Entity.course_offerings and semester["academic_year_id"] != values["academic_year_id"]:
                raise AppError("Offering year and semester must match", 422, "ACADEMIC_REFERENCE_INVALID")
        if entity == Entity.course_offerings:
            links = repository.list_records(client, institution_id, Entity.program_courses)
            if not any(link["is_active"] and link["program_id"] == values["program_id"]
                       and link["course_id"] == values["course_id"]
                       and link["semester_id"] in (None, values["semester_id"]) for link in links):
                raise AppError("Choose an active matching program-course link", 422, "ACADEMIC_REFERENCE_INVALID")
    elif entity == Entity.sections:
        offering = parent(Entity.course_offerings, "course_offering_id", "course offering")
        validate_structure_parents(client, institution_id, Entity.course_offerings, offering, None)
