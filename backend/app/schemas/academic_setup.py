"""Validated contracts for the existing academic master tables."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    create_model,
    field_validator,
)

Text = Annotated[str, Field(min_length=1, max_length=200)]
Positive = Annotated[float, Field(gt=0)]
Hours = Annotated[float, Field(ge=0)]
Capacity = Annotated[int, Field(gt=0, strict=True)]
Entity = Literal[
    "departments", "programs", "academic_years", "semesters", "courses",
    "program_courses", "course_offerings", "sections",
]


class MasterRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    is_active: StrictBool = True

    @field_validator("*", mode="after")
    @classmethod
    def nonblank(cls, value):
        if isinstance(value, str) and not value.strip():
            raise ValueError("Text must not be blank")
        return value


class NamedRecord(MasterRecord):
    name: Text
    code: Text


class DepartmentCreate(NamedRecord):
    description: Annotated[str, Field(max_length=4000)] | None = None


class ProgramCreate(DepartmentCreate):
    department_id: UUID
    degree_type: Text
    duration_years: Positive
    total_credits: Positive | None = None


class YearCreate(NamedRecord):
    start_date: date
    end_date: date
    is_current: StrictBool = False


class SemesterCreate(YearCreate):
    academic_year_id: UUID
    semester_number: Annotated[int, Field(gt=0, strict=True)]


class CourseCreate(DepartmentCreate):
    department_id: UUID
    credits: Positive | None = None
    lecture_hours: Hours | None = None
    tutorial_hours: Hours | None = None
    practical_hours: Hours | None = None


class CurriculumCreate(MasterRecord):
    program_id: UUID
    course_id: UUID
    semester_id: UUID | None = None
    course_type: Literal["core", "elective", "open_elective", "skill", "project"]
    is_required: StrictBool = True


class OfferingCreate(MasterRecord):
    course_id: UUID
    program_id: UUID
    academic_year_id: UUID
    semester_id: UUID
    capacity: Capacity | None = None


class SectionCreate(NamedRecord):
    course_offering_id: UUID
    capacity: Capacity | None = None


CREATE_MODELS = {
    "departments": DepartmentCreate, "programs": ProgramCreate,
    "academic_years": YearCreate, "semesters": SemesterCreate,
    "courses": CourseCreate, "program_courses": CurriculumCreate,
    "course_offerings": OfferingCreate, "sections": SectionCreate,
}
IDS = {
    "departments": "department_id", "programs": "program_id",
    "academic_years": "academic_year_id", "semesters": "semester_id",
    "courses": "course_id", "program_courses": "program_course_id",
    "course_offerings": "course_offering_id", "sections": "section_id",
}
# Academic ancestry is immutable. Section code participates in class scope.
IMMUTABLE = {
    entity: {field for field in model.model_fields if field.endswith("_id")}
    | ({"code"} if entity == "sections" else set())
    for entity, model in CREATE_MODELS.items()
}
UPDATE_MODELS = {
    entity: create_model(
        f"{model.__name__.removesuffix('Create')}Update",
        __base__=MasterRecord,
        **{
            name: (field.rebuild_annotation() | None, None)
            for name, field in model.model_fields.items()
            if name not in IMMUTABLE[entity]
        },
    )
    for entity, model in CREATE_MODELS.items()
}


def validate_payload(entity: str, payload: dict, updating: bool) -> dict:
    model = UPDATE_MODELS[entity] if updating else CREATE_MODELS[entity]
    validated = model.model_validate(payload).model_dump(mode="json", exclude_unset=updating)
    if updating:
        for name, value in validated.items():
            if value is None:
                # Revalidate explicit null against the original field contract.
                from pydantic import TypeAdapter

                TypeAdapter(CREATE_MODELS[entity].model_fields[name].rebuild_annotation()).validate_python(None)
    return validated
