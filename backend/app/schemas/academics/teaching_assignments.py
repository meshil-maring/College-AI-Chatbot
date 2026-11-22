"""Teaching assignment request bodies.

The browser names only the offering, the teacher and the dates. The database
derives the receiving department, whether approval is needed and who may act.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.academics.academic_setup import AcademicModel


class TeachingAssignmentCreate(AcademicModel):
    academic_offering_id: UUID
    faculty_user_id: UUID
    starts_on: date | None = None
    planned_end_on: date | None = None

    @model_validator(mode="after")
    def ordered_term(self):
        if self.starts_on and self.planned_end_on and self.planned_end_on < self.starts_on:
            raise ValueError("The planned end cannot be before the start date")
        return self


class TeachingAssignmentDecision(AcademicModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def trimmed(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @model_validator(mode="after")
    def reason_for_rejection(self):
        if self.action == "reject" and not self.note:
            raise ValueError("Give a reason for rejecting this request")
        return self
