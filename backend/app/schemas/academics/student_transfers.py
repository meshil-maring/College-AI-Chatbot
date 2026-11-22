"""Student transfer and Head of Department request bodies.

The browser never supplies a student, institution, source section or program:
the database derives them from the authenticated actor and current placement.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.academics.academic_setup import AcademicModel


class TransferSubmit(AcademicModel):
    to_section_id: UUID
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Explain the transfer in at least 10 characters")
        return value


class DirectTransfer(TransferSubmit):
    # An administrator or HOD names the student; the database checks tenant,
    # department scope and the student's current placement.
    student_id: UUID
    # Only an administrator may move a student to a different semester number;
    # the database refuses the flag for anyone else.
    allow_other_semester: bool = False


class TransferDecision(AcademicModel):
    action: Literal["start_review", "approve", "reject"]
    comment: str | None = Field(default=None, max_length=2000)


class DepartmentHeadWrite(AcademicModel):
    # None removes the current Head of Department.
    faculty_user_id: UUID | None


class DepartmentHeadTerm(AcademicModel):
    """HOD term. The start cannot be in the future; the planned end is optional."""

    starts_on: date
    planned_end_on: date | None = None

    @model_validator(mode="after")
    def _term(self):
        if self.planned_end_on is not None and self.planned_end_on < self.starts_on:
            raise ValueError("The planned end date cannot be before the start date")
        return self


class DepartmentHeadAdd(AcademicModel):
    # One more Head of Department for the department; existing heads stay.
    # Without a start date the appointment starts today.
    faculty_user_id: UUID
    starts_on: date | None = None
    planned_end_on: date | None = None

    @model_validator(mode="after")
    def _term(self):
        if self.planned_end_on is not None and self.starts_on is not None and self.planned_end_on < self.starts_on:
            raise ValueError("The planned end date cannot be before the start date")
        return self


class DepartmentHeadPolicy(AcademicModel):
    # Whether one faculty member may head several departments at once.
    allow_multi_department_hod: bool
