"""Contracts for Class In-Charge and Subject Coordinator responsibilities.

Like Head of Department, these are dated responsibilities of a Faculty member,
not roles. A Class In-Charge looks after one class section; a Subject
Coordinator coordinates one catalogue course. The institution comes from the
administrator's scope, never from the request.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

ResponsibilityKind = Literal["class_in_charge", "subject_coordinator"]


class MemberResponsibilityAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faculty_user_id: UUID
    responsibility: ResponsibilityKind
    # A class section for Class In-Charge, a catalogue course for Subject Coordinator.
    target_id: UUID
    # Without a start date the appointment starts today; it cannot start later.
    starts_on: date | None = None
    planned_end_on: date | None = None

    @model_validator(mode="after")
    def _term(self):
        start = self.starts_on or date.today()
        if self.planned_end_on is not None and self.planned_end_on < start:
            raise ValueError("The planned end date cannot be before the start date")
        return self


class MemberResponsibilityView(BaseModel):
    responsibility_id: UUID
    responsibility: ResponsibilityKind
    faculty_user_id: UUID
    faculty_name: str
    academic_section_id: UUID | None = None
    course_id: UUID | None = None
    target_code: str | None = None
    target_name: str | None = None
    starts_on: date
    planned_end_on: date | None = None
    ended_at: datetime | None = None
    is_current: bool


class MemberResponsibilityList(BaseModel):
    responsibilities: list[MemberResponsibilityView]
    total: int


class MemberResponsibilityResult(BaseModel):
    responsibility_id: UUID
    already_applied: bool
    message: str
