"""Schemas for invitation-only Super Admin registration (Phase 9).

No request carries a role, scope or institution: the granted role is the server
constant ``super_admin`` at platform scope.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.admin_invitations import (
    MAX_INVITE_EMAIL_LENGTH,
    MAX_NAME_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)


class SuperAdminInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=MAX_INVITE_EMAIL_LENGTH)

    @field_validator("email")
    @classmethod
    def _normalize(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class SuperAdminInvitationView(BaseModel):
    invitation_id: UUID
    email: str
    status: str
    expires_at: datetime | None = None
    created_at: datetime | None = None


class SuperAdminInviteCreatedResponse(BaseModel):
    invitation: SuperAdminInvitationView
    invitation_token: str
    invitation_url: str
    expires_in_hours: int


class SuperAdminInvitationListResponse(BaseModel):
    invitations: list[SuperAdminInvitationView]


class SuperAdminInvitePublicView(BaseModel):
    email: str
    status: str
    expires_at: datetime | None = None


class SuperAdminRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    confirm_password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    first_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    last_name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)

    @field_validator("password")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class SuperAdminRegisteredResponse(BaseModel):
    email: str
    role: str = "super_admin"
    message: str
