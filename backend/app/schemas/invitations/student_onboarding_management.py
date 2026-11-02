"""Contracts for authenticated pending-invitation management."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.invitations.student_onboarding import StudentInvitationView


class StudentInvitationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    student_name: str = Field(min_length=1, max_length=200)
    register_number: str = Field(min_length=1, max_length=128)
    university_roll_number: str | None = Field(default=None, max_length=128)
    academic_section_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

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


class StudentInvitationUpdateResponse(BaseModel):
    invitation: StudentInvitationView
    email_changed: bool
    delivery_status: Literal["sent", "failed"] | None = None
    delivery_message: str | None = None
