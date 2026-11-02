"""Strict contracts for admin-created student onboarding invitations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StudentIdentityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_name: str = Field(min_length=1, max_length=200)
    register_number: str = Field(min_length=1, max_length=128)
    university_roll_number: str | None = Field(default=None, max_length=128)
    email: EmailStr = Field(max_length=320)

    @field_validator("student_name", "register_number")
    @classmethod
    def clean_required_identity(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("university_roll_number")
    @classmethod
    def clean_optional_roll_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return value or None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class StudentInvitationCreateRequest(StudentIdentityInput):
    academic_section_id: UUID


class StudentInvitationBulkRow(StudentIdentityInput):
    source_row: int = Field(ge=2, le=501)


class StudentInvitationBulkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    academic_section_id: UUID
    students: list[StudentInvitationBulkRow] = Field(min_length=1, max_length=500)


class StudentInvitationView(BaseModel):
    invitation_id: UUID
    institution_id: UUID
    email: str
    student_name: str
    register_number: str
    university_roll_number: str | None
    academic_section_id: UUID
    section_name: str | None = None
    section_code: str | None = None
    batch_name: str | None = None
    batch_code: str | None = None
    status: Literal["pending", "accepted", "cancelled"] = "pending"
    expires_at: datetime
    created_at: datetime
    email_delivery_status: Literal["pending", "sent", "failed"] = "pending"
    email_delivery_attempts: int = 0
    resend_count: int = 0
    last_sent_at: datetime | None = None


class StudentInvitationCreatedResponse(BaseModel):
    invitation: StudentInvitationView
    delivery_status: Literal["sent", "failed"]
    delivery_message: str


class StudentInvitationListResponse(BaseModel):
    invitations: list[StudentInvitationView]


class StudentIdentityReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    register_number: str | None = Field(default=None, max_length=128)
    university_roll_number: str | None = Field(default=None, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_review_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @field_validator("register_number", "university_roll_number")
    @classmethod
    def normalize_review_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def validate_has_identifier(self) -> "StudentIdentityReviewRequest":
        if not any((self.email, self.register_number, self.university_roll_number)):
            raise ValueError("enter at least one student identifier")
        return self


class StudentIdentityAccountMatch(BaseModel):
    student_name: str
    email: str | None
    register_number: str | None
    university_roll_number: str | None
    approval_status: str
    account_status: str | None
    student_status: str
    is_active: bool
    has_signed_in: bool
    last_sign_in_at: datetime | None
    matches_email: bool
    matches_register_number: bool
    matches_university_roll_number: bool


class StudentIdentityInvitationMatch(BaseModel):
    student_name: str
    email: str
    register_number: str
    university_roll_number: str | None
    status: Literal["pending"]
    email_delivery_status: Literal["pending", "sent", "failed"]
    expires_at: datetime
    last_sent_at: datetime | None
    has_signed_in: bool
    matches_email: bool
    matches_register_number: bool
    matches_university_roll_number: bool


class StudentIdentityReviewResponse(BaseModel):
    students: list[StudentIdentityAccountMatch]
    invitations: list[StudentIdentityInvitationMatch]
    email_conflict_exists: bool = False


class StudentInvitationRowResult(BaseModel):
    row: int
    status: Literal["created", "failed", "duplicate"]
    invitation: StudentInvitationView | None = None
    delivery_status: Literal["sent", "failed"] | None = None
    message: str


class StudentInvitationBulkResponse(BaseModel):
    total: int
    created: int
    failed: int
    rows: list[StudentInvitationRowResult]


class StudentInvitationResendResponse(BaseModel):
    invitation: StudentInvitationView
    delivery_status: Literal["sent", "failed"]
    delivery_message: str


class StudentInvitationReassignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    academic_section_id: UUID


class StudentInvitationCancelResponse(BaseModel):
    invitation_id: UUID
    cancelled: bool


class StudentInvitationInspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=32, max_length=256)

    @field_validator("token")
    @classmethod
    def token_is_url_safe(cls, value: str) -> str:
        if not value.isascii() or not all(char.isalnum() or char in "_-" for char in value):
            raise ValueError("invalid setup token")
        return value


class StudentInvitationPublicView(BaseModel):
    status: Literal["pending", "accepted"]
    student_name: str
    email: str
    institution_name: str
    batch_name: str
    batch_code: str
    section_name: str
    section_active: bool
    expires_at: datetime


class StudentInvitationCompleteRequest(StudentInvitationInspectRequest):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("password must not be blank")
        return value


class StudentInvitationCompleteResponse(BaseModel):
    message: str
    completed: bool
