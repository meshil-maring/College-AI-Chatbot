"""Phase 8.1 request contracts for scoped permissions and assignments."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StaffPermissionGrantChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_codes: list[str] = Field(min_length=1, max_length=32)


class FacultyAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faculty_user_id: UUID
    section_id: UUID


class FacultyAssignmentRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: UUID
