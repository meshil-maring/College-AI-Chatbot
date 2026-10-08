"""Strict contracts: identities and tenants are supplied by the server."""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator


class AssignmentValidity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_at: AwareDatetime
    end_at: AwareDatetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class ResponsibilityCreate(AssignmentValidity):
    faculty_user_id: UUID
    responsibility_code: str
    scope_type: Literal["institution", "department", "program", "semester", "section", "course"]
    scope_id: UUID
    program_id: UUID | None = None


class ResponsibilityUpdate(AssignmentValidity):
    scope_type: Literal["institution", "department", "program", "semester", "section", "course"]
    scope_id: UUID
    program_id: UUID | None = None


class ScopedTeachingAssignmentCreate(AssignmentValidity):
    faculty_user_id: UUID
    section_id: UUID
