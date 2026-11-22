"""Contracts for institution administrators and the Owner (User Management U2).

The Owner is an administrator with protected authority: only the Owner invites
or removes administrators and transfers ownership. The institution always comes
from the signed-in administrator's scope.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class InstitutionAdmin(BaseModel):
    user_id: UUID
    name: str
    email: str
    status: str
    assigned_at: datetime | str | None = None
    is_owner: bool = False


class AdminInvitationView(BaseModel):
    invitation_id: UUID
    email: str
    full_name: str | None = None
    expires_at: datetime | str | None = None
    created_at: datetime | str | None = None
    email_delivery_status: str | None = None


class InstitutionAdminList(BaseModel):
    owner_user_id: UUID | None
    # Whether the signed-in administrator is the Owner (and may manage administrators).
    viewer_is_owner: bool
    administrators: list[InstitutionAdmin]
    invitations: list[AdminInvitationView]


class AdminInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        trimmed = " ".join((value or "").split())
        return trimmed or None


class OwnershipTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID


class InstitutionAdminResult(BaseModel):
    message: str
    already_applied: bool = False
