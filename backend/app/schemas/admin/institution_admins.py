"""Contracts for institution administrators and the Owner (User Management U2).

The Owner is an administrator with protected authority: only the Owner invites
or removes administrators and transfers ownership. The institution always comes
from the signed-in administrator's scope.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# Areas the Owner can allow an administrator; the database maps them to
# permission codes. None means full access (every area, and future permissions).
AccessArea = Literal[
    "staff_faculty", "students", "academic_setup", "content", "staff_permissions", "settings_audit",
]


def _unique_areas(value: list[str] | None) -> list[str] | None:
    if value is not None and len(set(value)) != len(value):
        raise ValueError("Choose each access area once")
    return value


class InstitutionAdmin(BaseModel):
    user_id: UUID
    name: str
    email: str
    status: str
    assigned_at: datetime | str | None = None
    is_owner: bool = False
    access_areas: list[str] | None = None


class AdminInvitationView(BaseModel):
    invitation_id: UUID
    email: str
    full_name: str | None = None
    expires_at: datetime | str | None = None
    created_at: datetime | str | None = None
    email_delivery_status: str | None = None
    access_areas: list[str] | None = None


class InstitutionAdminList(BaseModel):
    owner_user_id: UUID | None
    # Whether the signed-in administrator is the Owner (and may manage administrators).
    viewer_is_owner: bool
    administrators: list[InstitutionAdmin]
    invitations: list[AdminInvitationView]
    access_area_options: list[str] = []


class AdminInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    full_name: str | None = Field(default=None, max_length=200)
    access_areas: list[AccessArea] | None = None

    @field_validator("access_areas")
    @classmethod
    def _areas(cls, value: list[str] | None) -> list[str] | None:
        return _unique_areas(value)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        trimmed = " ".join((value or "").split())
        return trimmed or None


class AdminAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # None or every area gives full access; an empty list leaves only the basics.
    access_areas: list[AccessArea] | None

    @field_validator("access_areas")
    @classmethod
    def _areas(cls, value: list[str] | None) -> list[str] | None:
        return _unique_areas(value)


class OwnershipTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID


class InstitutionAdminResult(BaseModel):
    message: str
    already_applied: bool = False
