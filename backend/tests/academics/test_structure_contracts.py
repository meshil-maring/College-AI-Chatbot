"""Contracts exercise the eight supplied tables and reject the prior model."""
import pytest
from pydantic import ValidationError

from app.schemas.academics.academic_setup import AcademicEntity as Entity, CREATE_MODELS, UPDATE_MODELS
from app.repositories.academics.academic_setup import PRIMARY_KEYS
from .support import setup_rows


@pytest.mark.parametrize("entity", list(Entity))
def test_export_record_round_trips_without_client_tenant_or_primary_key(entity):
    record = setup_rows()[entity]
    payload = {key: value for key, value in record.items() if key not in {PRIMARY_KEYS[entity], "institution_id"}}
    assert CREATE_MODELS[entity].model_validate(payload).model_dump(mode="json") == payload
    for key in ("institution_id", PRIMARY_KEYS[entity], "actor_id"):
        with pytest.raises(ValidationError):
            CREATE_MODELS[entity].model_validate({**payload, key: record.get(key, "injected")})


@pytest.mark.parametrize("entity,field", [
    (Entity.programs, "department_id"), (Entity.courses, "department_id"),
    (Entity.semesters, "academic_year_id"), (Entity.program_courses, "program_id"),
    (Entity.program_courses, "course_id"), (Entity.program_courses, "semester_id"),
    (Entity.course_offerings, "program_id"), (Entity.course_offerings, "semester_id"),
    (Entity.sections, "course_offering_id"), (Entity.sections, "code"),
])
def test_parent_references_and_section_code_are_immutable(entity, field):
    with pytest.raises(ValidationError):
        UPDATE_MODELS[entity].model_validate({field: setup_rows()[entity][field]})


@pytest.mark.parametrize("entity", list(Entity))
def test_empty_patch_and_null_active_are_rejected(entity):
    for payload in ({}, {"is_active": None}, {"is_active": "false"}):
        with pytest.raises(ValidationError):
            UPDATE_MODELS[entity].model_validate(payload)


def test_course_nullable_credits_and_zero_hours_follow_export():
    model = UPDATE_MODELS[Entity.courses](credits=None, lecture_hours=0, practical_hours=2.5)
    assert model.credits is None and model.lecture_hours == 0
    with pytest.raises(ValidationError):
        UPDATE_MODELS[Entity.courses](lecture_hours=-1)


@pytest.mark.parametrize("capacity", [0, -1, 1.5, True, float("inf")])
def test_capacity_is_a_positive_integer(capacity):
    with pytest.raises(ValidationError):
        UPDATE_MODELS[Entity.course_offerings](capacity=capacity)


def test_semester_requires_dates_and_has_no_program_or_study_number():
    with pytest.raises(ValidationError):
        CREATE_MODELS[Entity.semesters](name="Fifth", code="S5", program_id="old", study_semester_number=5)
    assert Entity.programs.permission_resource == "departments"
    assert Entity.sections.permission_resource == "courses"
