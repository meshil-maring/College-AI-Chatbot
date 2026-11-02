"""Contracts for the institution-admin student directory."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

StudentDirectoryFilter = Literal["pending_sign_in", "signed_in", "no_signin"]
StudentDirectoryStatus = Literal["pending_sign_in", "signed_in", "no_signin"]


class StudentDirectoryRow(BaseModel):
    record_id: UUID
    record_type: Literal["student", "invitation"]
    student_name: str
    email: str | None
    register_number: str | None
    university_roll_number: str | None
    status: StudentDirectoryStatus
    approval_status: str | None
    account_status: str | None
    student_status: str | None
    is_active: bool | None
    last_sign_in_at: datetime | None
    email_delivery_status: Literal["pending", "sent", "failed"] | None
    expires_at: datetime | None
    program_id: UUID | None
    program_name: str | None
    program_code: str | None
    course_name: str | None
    branch_name: str | None
    branch_code: str | None
    batch_name: str | None
    batch_code: str | None
    admission_cohort_id: UUID | None = None
    section_name: str | None
    section_code: str | None
    academic_section_id: UUID | None = None
    created_at: datetime


class StudentDirectorySummary(BaseModel):
    total: int
    pending_sign_in: int
    signed_in: int
    no_signin: int


class StudentDirectoryProgram(BaseModel):
    program_id: UUID
    program_name: str
    program_code: str


class StudentDirectoryResponse(BaseModel):
    items: list[StudentDirectoryRow]
    total: int
    limit: int
    offset: int
    summary: StudentDirectorySummary
    programs: list[StudentDirectoryProgram]


class StudentProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_name: str = Field(min_length=1, max_length=200)
    register_number: str = Field(min_length=1, max_length=128)
    university_roll_number: str | None = Field(default=None, max_length=128)
    academic_section_id: UUID | None = None

    @field_validator("student_name", "register_number")
    @classmethod
    def normalize_required_identity(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("This field cannot be blank")
        return normalized

    @field_validator("university_roll_number")
    @classmethod
    def normalize_optional_roll(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class StudentActiveResponse(BaseModel):
    student_id: UUID
    is_active: bool


class StudentProfileMutationResponse(BaseModel):
    student_id: UUID
    updated: bool


class StudentDeletionResponse(BaseModel):
    student_id: UUID
    deleted: bool
