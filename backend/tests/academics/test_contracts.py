"""Request validation keeps tenant, actor and immutable parents server-owned."""

import pytest
from pydantic import ValidationError

from app.schemas.academics.academic_setup import (
    AcademicYearCreate,
    AcademicYearUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    ProgramCreate,
    ProgramUpdate,
)
from .support import DEPARTMENT


@pytest.mark.parametrize("field", ["institution_id", "actor_id", "department_id", "created_at"])
def test_department_rejects_unknown_authority_and_metadata(field):
    with pytest.raises(ValidationError):
        DepartmentCreate.model_validate({"name": "CSE", "code": "CSE", field: "injected"})


@pytest.mark.parametrize("model", [DepartmentUpdate, ProgramUpdate, AcademicYearUpdate])
@pytest.mark.parametrize("payload", [{}, {"name": None}, {"code": None}, {"is_active": None}])
def test_patch_rejects_empty_or_null_required_values(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize("value", [None, 0, -1, float("nan"), float("inf"), True])
def test_program_rejects_invalid_duration(value):
    with pytest.raises(ValidationError):
        ProgramCreate.model_validate({
            "department_id": DEPARTMENT, "name": "B.Tech CSE", "code": "BTCSE",
            "degree_type": "B.Tech", "duration_years": value,
        })


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_program_rejects_invalid_credits(value):
    with pytest.raises(ValidationError):
        ProgramUpdate(total_credits=value)


def test_program_parent_cannot_be_changed():
    with pytest.raises(ValidationError):
        ProgramUpdate.model_validate({"department_id": DEPARTMENT})


def test_optional_description_and_credits_can_be_cleared():
    assert ProgramUpdate(description=None, total_credits=None).model_dump(
        exclude_unset=True
    ) == {"description": None, "total_credits": None}


def test_fractional_durations_and_credits_are_supported():
    program = ProgramCreate(
        department_id=DEPARTMENT, name="Degree", code="DEG", degree_type="Degree",
        duration_years=2.5, total_credits=80.5,
    )
    assert program.duration_years == 2.5
    assert program.total_credits == 80.5


@pytest.mark.parametrize("value", ["false", "true", 0, 1])
def test_flags_require_actual_booleans(value):
    with pytest.raises(ValidationError):
        DepartmentUpdate(is_active=value)


@pytest.mark.parametrize("dates", [
    {"start_date": "2027-07-01", "end_date": "2027-07-01"},
    {"start_date": "2027-07-01", "end_date": "2026-07-01"},
    {"start_date": "invalid", "end_date": "2027-06-30"},
])
def test_year_requires_ordered_calendar_dates(dates):
    with pytest.raises(ValidationError):
        AcademicYearCreate(name="2026–2027", code="2026-27", **dates)


def test_current_year_cannot_be_inactive():
    with pytest.raises(ValidationError):
        AcademicYearUpdate(is_current=True, is_active=False)


def test_department_trims_names_and_rejects_blank_codes():
    assert DepartmentCreate(name=" CSE ", code=" CSE ").name == "CSE"
    with pytest.raises(ValidationError):
        DepartmentCreate(name="CSE", code=" ")
