"""Validate the active ancestry for Academic Setup entities."""

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
            raise AppError("Term dates must fit its academic year", 422, "ACADEMIC_REFERENCE_INVALID")
    if not check_active:
        return

    def parent(kind, key, label):
        return active_parent(client, institution_id, kind, values[key], label)

    if entity in {Entity.programs, Entity.courses}:
        parent(Entity.departments, "department_id", "department")
    elif entity == Entity.semesters:
        parent(Entity.academic_years, "academic_year_id", "academic year")
