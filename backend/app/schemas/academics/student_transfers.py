"""Student transfer and Head of Department request bodies.

The browser never supplies a student, institution, source section or program:
the database derives them from the authenticated actor and current placement.
"""

from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

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


class TransferDecision(AcademicModel):
    action: Literal["start_review", "approve", "reject"]
    comment: str | None = Field(default=None, max_length=2000)


class DepartmentHeadWrite(AcademicModel):
    # None removes the current Head of Department.
    faculty_user_id: UUID | None
