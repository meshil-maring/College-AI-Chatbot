"""Phase 8.1 request contracts for scoped permissions and assignments."""

from uuid import UUID
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class StaffPermissionGrantChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_codes: list[str] = Field(min_length=1, max_length=32)


class FacultyAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faculty_user_id: UUID
    section_id: UUID
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if not self.is_active and self.start_at is None:
            raise ValueError("Disabled teaching assignments require explicit validity")
        if self.end_at and (not self.start_at or self.end_at <= self.start_at):
            raise ValueError("end_at requires start_at and must be later")
        return self


class FacultyAssignmentRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: UUID
