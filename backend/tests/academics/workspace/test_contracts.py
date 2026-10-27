from uuid import uuid4

from pydantic import ValidationError
import pytest

from app.schemas.academics.academic_structure import CREATE_MODELS, UPDATE_MODELS, StructureEntity as Entity
from ..support import PROGRAM, YEAR, COURSE, SEMESTER


def payloads():
    parent = str(uuid4())
    return {
        Entity.program_semesters: {"program_id": PROGRAM, "name": "Semester 1", "code": "S1", "semester_number": 1},
        Entity.curriculum_versions: {"program_id": PROGRAM, "academic_year_id": YEAR, "name": "CSE", "version": "1.0", "total_semesters": 8},
        Entity.curriculum_subjects: {"curriculum_version_id": parent, "program_semester_id": parent, "course_id": COURSE},
        Entity.admission_cohorts: {"program_id": PROGRAM, "academic_year_id": YEAR, "curriculum_version_id": parent, "name": "CSE 2026", "code": "CSE26", "start_year": 2026, "end_year": 2030},
        Entity.academic_sections: {"admission_cohort_id": parent, "program_semester_id": parent, "semester_id": SEMESTER, "name": "A", "code": "CSE26A"},
        Entity.academic_offerings: {"academic_section_id": parent, "curriculum_subject_id": parent},
    }


@pytest.mark.parametrize("entity", list(Entity))
def test_create_defaults_and_actor_tenant_rejection(entity):
    payload = payloads()[entity]
    CREATE_MODELS[entity].model_validate(payload)
    for field in ("institution_id", "actor_user_id"):
        with pytest.raises(ValidationError):
            CREATE_MODELS[entity].model_validate({**payload, field: str(uuid4())})


@pytest.mark.parametrize("entity", list(Entity))
def test_updates_require_changes_and_reject_parent_reassignment(entity):
    with pytest.raises(ValidationError):
        UPDATE_MODELS[entity].model_validate({})
    for field, value in payloads()[entity].items():
        if field.endswith("_id") or field in {"semester_number", "version", "total_semesters", "start_year", "end_year"}:
            with pytest.raises(ValidationError):
                UPDATE_MODELS[entity].model_validate({field: value})


@pytest.mark.parametrize("value", [-1, 1.5, True, "60", 2147483648])
def test_capacity_is_a_bounded_strict_whole_number(value):
    with pytest.raises(ValidationError):
        CREATE_MODELS[Entity.academic_sections].model_validate({**payloads()[Entity.academic_sections], "capacity": value})


def test_optional_values_clear_without_nulling_required_fields():
    assert UPDATE_MODELS[Entity.academic_sections].model_validate({"capacity": None, "description": None})
    assert UPDATE_MODELS[Entity.admission_cohorts].model_validate({"expected_count": None})
    with pytest.raises(ValidationError):
        UPDATE_MODELS[Entity.curriculum_versions].model_validate({"status": None})
    with pytest.raises(ValidationError):
        CREATE_MODELS[Entity.admission_cohorts].model_validate({**payloads()[Entity.admission_cohorts], "end_year": 2025})


def test_publication_and_student_counts_are_server_owned():
    with pytest.raises(ValidationError):
        CREATE_MODELS[Entity.curriculum_versions].model_validate({**payloads()[Entity.curriculum_versions], "status": "published"})
    with pytest.raises(ValidationError):
        CREATE_MODELS[Entity.admission_cohorts].model_validate({**payloads()[Entity.admission_cohorts], "student_count": 120})
