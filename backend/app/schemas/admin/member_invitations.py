"""Contracts for Staff and Faculty invited by an institution administrator."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.admin.admin_memberships import MembershipRole
from app.schemas.invitations.admin_invitations import EmailDeliveryOutcome


class MemberInvitationCreate(BaseModel):
    """Everything the administrator chooses. Institution, expiry and token are server-side."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    full_name: str = Field(min_length=1, max_length=200)
    role: MembershipRole
    department_id: UUID

    @field_validator("email")
    @classmethod
    def _email_normalized(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def _name_trimmed(cls, value: str) -> str:
        trimmed = " ".join(value.split())
        if not trimmed:
            raise ValueError("Enter the person's name")
        return trimmed


class MemberInvitationView(BaseModel):
    """A Staff/Faculty invitation without its token or digest."""

    invitation_id: UUID
    email: str
    full_name: str | None
    role: MembershipRole
    department_id: UUID | None
    status: Literal["invited", "accepted", "cancelled", "expired"]
    expires_at: datetime | str | None
    created_at: datetime | str | None
    email_delivery_status: str
    resend_count: int = 0
    last_sent_at: datetime | str | None = None


class MemberInvitationList(BaseModel):
    invitations: list[MemberInvitationView]
    total: int


class MemberInvitationCreated(BaseModel):
    invitation: MemberInvitationView
    email_delivery: EmailDeliveryOutcome
    expires_in_hours: int
    message: str


class MemberInvitationCancelled(BaseModel):
    invitation_id: UUID
    already_applied: bool
    message: str
