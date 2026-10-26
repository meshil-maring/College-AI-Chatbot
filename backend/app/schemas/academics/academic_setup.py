"""Academic Setup contracts matching the owner's exported relational schema."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator


class AcademicEntity(StrEnum):
    departments = "departments"
    programs = "programs"
    academic_years = "academic_years"
    semesters = "semesters"
    courses = "courses"
    program_courses = "program_courses"
    course_offerings = "course_offerings"
    sections = "sections"

    @property
    def permission_resource(self):
        if self == self.programs:
            return "departments"
        if self in {self.program_courses, self.course_offerings, self.sections}:
            return "courses"
        return self.value


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Positive = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]
Hours = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Capacity = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
SemesterNumber = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class AcademicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MasterCreate(AcademicModel):
    name: Name
    code: Code
    is_active: StrictBool = True


class DepartmentCreate(MasterCreate):
    description: Description | None = None


class ProgramCreate(DepartmentCreate):
    department_id: UUID
    degree_type: Name
    duration_years: Positive
    total_credits: Annotated[float, Field(strict=True, allow_inf_nan=False)] | None = None


class AcademicYearCreate(MasterCreate):
    start_date: date
    end_date: date
    is_current: StrictBool = False

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        if self.is_current and not self.is_active:
            raise ValueError("The current academic period must be active")
        return self


class SemesterCreate(AcademicYearCreate):
    academic_year_id: UUID
    semester_number: SemesterNumber


class CourseCreate(DepartmentCreate):
    department_id: UUID
    credits: Positive | None = None
    lecture_hours: Hours | None = None
    tutorial_hours: Hours | None = None
    practical_hours: Hours | None = None


class CourseType(StrEnum):
    core = "core"
    elective = "elective"
    open_elective = "open_elective"
    skill = "skill"
    project = "project"


class ProgramCourseCreate(AcademicModel):
    program_id: UUID
    course_id: UUID
    semester_id: UUID | None = None
    course_type: CourseType
    is_required: StrictBool = True
    is_active: StrictBool = True


class CourseOfferingCreate(AcademicModel):
    course_id: UUID
    program_id: UUID
    academic_year_id: UUID
    semester_id: UUID
    capacity: Capacity | None = None
    is_active: StrictBool = True


class SectionCreate(MasterCreate):
    course_offering_id: UUID
    capacity: Capacity | None = None


class MasterUpdate(AcademicModel):
    name: Name | None = None
    code: Code | None = None
    is_active: StrictBool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        nullable = {"description", "total_credits", "credits", "lecture_hours", "tutorial_hours", "practical_hours", "capacity"}
        if any(getattr(self, key) is None for key in self.model_fields_set - nullable):
            raise ValueError("Required fields cannot be null")
        return self


class DepartmentUpdate(MasterUpdate):
    description: Description | None = None


class ProgramUpdate(DepartmentUpdate):
    degree_type: Name | None = None
    duration_years: Positive | None = None
    total_credits: Annotated[float, Field(strict=True, allow_inf_nan=False)] | None = None


class AcademicYearUpdate(MasterUpdate):
    start_date: date | None = None
    end_date: date | None = None
    is_current: StrictBool | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        if self.is_current is True and self.is_active is False:
            raise ValueError("The current academic period must be active")
        return self


class SemesterUpdate(AcademicYearUpdate):
    semester_number: SemesterNumber | None = None


class CourseUpdate(DepartmentUpdate):
    credits: Positive | None = None
    lecture_hours: Hours | None = None
    tutorial_hours: Hours | None = None
    practical_hours: Hours | None = None


class RelationUpdate(AcademicModel):
    is_active: StrictBool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set or any(
            getattr(self, key) is None for key in self.model_fields_set - {"capacity"}
        ):
            raise ValueError("Provide non-null changes")
        return self


class ProgramCourseUpdate(RelationUpdate):
    course_type: CourseType | None = None
    is_required: StrictBool | None = None


class CourseOfferingUpdate(RelationUpdate):
    capacity: Capacity | None = None


class SectionUpdate(RelationUpdate):
    name: Name | None = None
    capacity: Capacity | None = None


CREATE_MODELS = dict(zip(AcademicEntity, (
    DepartmentCreate, ProgramCreate, AcademicYearCreate, SemesterCreate,
    CourseCreate, ProgramCourseCreate, CourseOfferingCreate, SectionCreate,
)))
UPDATE_MODELS = dict(zip(AcademicEntity, (
    DepartmentUpdate, ProgramUpdate, AcademicYearUpdate, SemesterUpdate,
    CourseUpdate, ProgramCourseUpdate, CourseOfferingUpdate, SectionUpdate,
)))


class AcademicSetupResponse(AcademicModel):
    institution_id: UUID
    records: dict[AcademicEntity, list[dict]]
    manageable: list[AcademicEntity]
