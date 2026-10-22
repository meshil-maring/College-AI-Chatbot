"""Typed commands for versioned curricula, classes and complete packages."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

Name = Annotated[str, Field(min_length=1, max_length=200)]
Code = Annotated[str, Field(min_length=1, max_length=64)]
Reason = Annotated[str, Field(min_length=1, max_length=2000)]
StudySemester = Annotated[int, Field(ge=1, le=30, strict=True)]
CourseType = Literal["core", "elective", "open_elective", "skill", "project"]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SaveCurriculum(Command):
    curriculum_id: UUID | None = None
    program_id: UUID
    name: Name
    code: Code
    version: Annotated[int, Field(ge=1, le=1000, strict=True)]


class SetCurriculumSubject(Command):
    curriculum_id: UUID
    course_id: UUID
    study_semester: StudySemester
    course_type: CourseType
    is_core: StrictBool


class SavePackage(Command):
    package_id: UUID | None = None
    curriculum_id: UUID
    study_semester: StudySemester
    name: Name
    code: Code
    curriculum_subject_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]

    @field_validator("curriculum_subject_ids")
    @classmethod
    def unique_subjects(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Package subjects must be unique")
        return values


class SaveClass(Command):
    class_id: UUID | None = None
    program_id: UUID
    batch_id: UUID
    semester_id: UUID
    study_semester: StudySemester
    section_code: Annotated[str, Field(min_length=1, max_length=128)]
    curriculum_id: UUID
    student_choice_enabled: StrictBool
    change_cutoff: datetime | None = None

    @field_validator("change_cutoff")
    @classmethod
    def aware_cutoff(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Change cutoff must include a timezone")
        return value


class SetClassPackage(Command):
    class_id: UUID
    package_id: UUID
    enabled: StrictBool


class SetClassSubject(Command):
    class_id: UUID
    curriculum_subject_id: UUID
    section_id: UUID


class PrepareClassTeaching(Command):
    class_id: UUID


class PlaceStudent(Command):
    class_id: UUID
    registration_id: UUID


class SetClassResponsibility(Command):
    class_id: UUID
    responsibility_id: UUID
    enabled: StrictBool


class AssignPackage(Command):
    placement_id: UUID
    package_id: UUID


class ChangePackage(Command):
    assignment_id: UUID
    package_id: UUID
    expected_revision: Annotated[int, Field(ge=1, strict=True)]
    reason: Reason


class RequestChange(Command):
    assignment_id: UUID
    package_id: UUID
    reason: Reason


class ReviewRequest(Command):
    request_id: UUID
    approve: StrictBool
    reason: Reason


COMMAND_MODELS = {
    "save_curriculum": SaveCurriculum,
    "set_curriculum_subject": SetCurriculumSubject,
    "save_package": SavePackage,
    "save_class": SaveClass,
    "set_class_package": SetClassPackage,
    "set_class_subject": SetClassSubject,
    "prepare_class_teaching": PrepareClassTeaching,
    "place_student": PlaceStudent,
    "set_class_responsibility": SetClassResponsibility,
    "assign_package": AssignPackage,
    "change_package": ChangePackage,
    "request_change": RequestChange,
    "review_request": ReviewRequest,
}


def validate_command(operation: str, payload: dict) -> dict:
    """Only known command fields reach the authoritative database operation."""
    return COMMAND_MODELS[operation].model_validate(payload).model_dump(
        mode="json", exclude_unset=True,
    )
