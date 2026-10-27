"""Additive contracts for versioned curricula, cohorts and class delivery."""

from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, StrictBool, model_validator

from app.schemas.academics.academic_setup import (
    AcademicModel, Code, Description, MasterCreate, Name,
)


Count = Annotated[int, Field(strict=True, ge=0, le=2147483647)]
StageNumber = Annotated[int, Field(strict=True, ge=1, le=32)]
YearNumber = Annotated[int, Field(strict=True, ge=1900, le=2200)]


class StructureUpdate(AcademicModel):
    is_active: StrictBool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        nullable = {"capacity", "description"}
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set - nullable
        ):
            raise ValueError("Provide non-null required changes")
        return self


class StructureEntity(StrEnum):
    program_semesters = "program_semesters"
    curriculum_versions = "curriculum_versions"
    curriculum_subjects = "curriculum_subjects"
    admission_cohorts = "admission_cohorts"
    academic_sections = "academic_sections"
    academic_offerings = "academic_offerings"

    @property
    def permission_resource(self):
        if self in {self.program_semesters, self.admission_cohorts}:
            return "departments"
        return "courses"


class ProgramSemesterCreate(MasterCreate):
    program_id: UUID
    semester_number: StageNumber


class ProgramSemesterUpdate(StructureUpdate):
    name: Name | None = None
    code: Code | None = None


class CurriculumVersionCreate(AcademicModel):
    program_id: UUID
    academic_year_id: UUID
    name: Name
    version: Code
    total_semesters: StageNumber
    description: Description | None = None
    is_active: StrictBool = True


class CurriculumVersionUpdate(StructureUpdate):
    name: Name | None = None
    description: Description | None = None
    status: Annotated[str, Field(pattern="^(draft|published|archived)$")] | None = None


class CurriculumSubjectCreate(AcademicModel):
    curriculum_version_id: UUID
    program_semester_id: UUID
    course_id: UUID
    course_type: Annotated[str, Field(pattern="^(core|elective|open_elective|skill|project)$")] = "core"
    is_required: StrictBool = True
    is_active: StrictBool = True


class CurriculumSubjectUpdate(StructureUpdate):
    course_type: Annotated[str, Field(pattern="^(core|elective|open_elective|skill|project)$")] | None = None
    is_required: StrictBool | None = None


class CohortCreate(AcademicModel):
    program_id: UUID
    curriculum_version_id: UUID
    academic_year_id: UUID
    name: Name
    code: Code
    start_year: YearNumber
    end_year: YearNumber
    expected_count: Count | None = None
    description: Description | None = None
    status: Annotated[str, Field(pattern="^(active|completed|inactive)$")] = "active"

    @model_validator(mode="after")
    def validate_years(self) -> Self:
        if self.end_year <= self.start_year:
            raise ValueError("End year must be later than start year")
        return self


class CohortUpdate(AcademicModel):
    name: Name | None = None
    code: Code | None = None
    expected_count: Count | None = None
    description: Description | None = None
    status: Annotated[str, Field(pattern="^(active|completed|inactive)$")] | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for field in self.model_fields_set - {"description", "expected_count"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class AcademicSectionCreate(MasterCreate):
    admission_cohort_id: UUID
    program_semester_id: UUID
    semester_id: UUID
    capacity: Count | None = None
    description: Description | None = None


class AcademicSectionUpdate(StructureUpdate):
    name: Name | None = None
    capacity: Count | None = None
    description: Description | None = None


class AcademicOfferingCreate(AcademicModel):
    academic_section_id: UUID
    curriculum_subject_id: UUID
    capacity: Count | None = None
    is_active: StrictBool = True


class AcademicOfferingUpdate(StructureUpdate):
    capacity: Count | None = None


CREATE_MODELS = dict(zip(StructureEntity, (
    ProgramSemesterCreate, CurriculumVersionCreate, CurriculumSubjectCreate,
    CohortCreate, AcademicSectionCreate, AcademicOfferingCreate,
), strict=True))
UPDATE_MODELS = dict(zip(StructureEntity, (
    ProgramSemesterUpdate, CurriculumVersionUpdate, CurriculumSubjectUpdate,
    CohortUpdate, AcademicSectionUpdate, AcademicOfferingUpdate,
), strict=True))


class StructureResponse(AcademicModel):
    institution_id: UUID
    records: dict[StructureEntity, list[dict]]
    manageable: list[StructureEntity]
    activities: list[dict] = Field(default_factory=list)
