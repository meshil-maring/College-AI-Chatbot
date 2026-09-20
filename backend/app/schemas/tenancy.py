"""Phase 6.13 — Organization / institution / staff-faculty API contracts.

Security invariants baked into these schemas:

* ``extra="forbid"`` everywhere — clients can NEVER inject ``role``,
  ``scope_type``, ``scope_id``, ``status``, ``approval_status`` or any other
  authorization-control field. Role and scope are decided ONLY server-side.
* Public registration payloads never accept internal database ids; they use
  the public codes (``organization_code`` / ``institution_code``), which the
  server resolves to ids.
* ``requested_role`` for staff/faculty registration is a pydantic ``Literal``
  restricted to ``staff | faculty`` — a privilege-escalation request ("admin")
  is unrepresentable and rejected with 422 before any service call.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def _password_min_length(value: str) -> str:
    if len(value) < 6:
        raise ValueError("Password must be at least 6 characters")
    return value


class OrganizationRegistrationRequest(BaseModel):
    """Public organization registration payload.

    The submitting user becomes the initial ORGANIZATION ADMIN. The role and
    scope are assigned server-side — the payload cannot influence them.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    organization_code: str = Field(min_length=2, max_length=64)
    official_email: EmailStr
    contact_information: str
    admin_email: EmailStr
    admin_password: str
    admin_first_name: str
    admin_last_name: str

    @field_validator("name", "contact_information", "admin_first_name", "admin_last_name")
    @classmethod
    def _names_not_blank(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("organization_code")
    @classmethod
    def _code_normalized(cls, v: str) -> str:
        return _not_blank(v).upper()

    @field_validator("admin_password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _password_min_length(v)


class OrganizationResponse(BaseModel):
    """Response after organization registration — clearly pending approval."""

    message: str
    organization_id: UUID
    organization_code: str
    status: str
    admin_user_id: UUID
    email: EmailStr


class InstitutionRegistrationRequest(BaseModel):
    """Public institution registration payload (join request to an organization).

    The organization is identified by its PUBLIC code plus the
    organization-issued join code when one exists. The submitting user becomes
    the initial INSTITUTION ADMIN; the institution starts ``pending`` and gains
    access only when an organization admin approves the join request.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    institution_code: str = Field(min_length=2, max_length=64)
    organization_code: str = Field(min_length=2, max_length=64)
    join_code: str | None = None
    official_email: EmailStr
    location: str | None = None
    admin_email: EmailStr
    admin_password: str
    admin_first_name: str
    admin_last_name: str

    @field_validator("name", "admin_first_name", "admin_last_name")
    @classmethod
    def _names_not_blank(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("institution_code", "organization_code")
    @classmethod
    def _code_normalized(cls, v: str) -> str:
        return _not_blank(v).upper()

    @field_validator("join_code", "location")
    @classmethod
    def _optional_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("admin_password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _password_min_length(v)


class InstitutionRegistrationResponse(BaseModel):
    """Response after institution registration — pending organization approval."""

    message: str
    institution_id: UUID
    institution_code: str
    organization_id: UUID
    status: str
    admin_user_id: UUID
    email: EmailStr


class InstitutionLookupResponse(BaseModel):
    """SAFE public institution projection for registration discovery.

    Phase 6.15.2 — deliberately minimal: only the fields an unauthenticated
    prospective student needs to confirm they are registering under the right
    institution. Never exposes contact information, location, organization
    linkage, status machinery, join codes, or any other internal column.
    """

    institution_id: UUID
    code: str
    name: str


class StaffFacultyRegistrationRequest(BaseModel):
    """Public staff/faculty registration payload.

    ``requested_role`` is a Literal of the two NON-privileged academic roles —
    the request ledger never records (and the API never accepts) an
    ``admin`` request. NO role is granted at registration; the role is written
    to user_roles server-side during admin approval only.
    """

    model_config = ConfigDict(extra="forbid")

    institution_code: str = Field(min_length=2, max_length=64)
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    requested_role: Literal["staff", "faculty"]
    designation: str | None = None
    department: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _names_not_blank(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("institution_code")
    @classmethod
    def _code_normalized(cls, v: str) -> str:
        return _not_blank(v).upper()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _password_min_length(v)

    @field_validator("designation", "department")
    @classmethod
    def _optional_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class StaffFacultyRegistrationResponse(BaseModel):
    """Response after staff/faculty registration — pending admin approval."""

    message: str
    request_id: UUID
    institution_id: UUID
    requested_role: str
    email: EmailStr


class ApprovalDecisionRequest(BaseModel):
    """Approve/reject payload. ``extra="forbid"`` — no decision spoofing."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _reason_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class DecisionResponse(BaseModel):
    """Response after an approval/rejection decision."""

    message: str
    status: str


class AuthorizationContextResponse(BaseModel):
    """Phase 6.13 identity + scope context of the authenticated user.

    Drives role-based frontend routing; the backend remains authoritative —
    this context is resolved SERVER-SIDE from user_roles, never from a
    client-supplied claim.
    """

    authenticated: bool = True
    user_id: UUID
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    scope_type: str | None = None
    scope_id: UUID | None = None
    organization_id: UUID | None = None
    institution_id: UUID | None = None
