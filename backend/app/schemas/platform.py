"""Phase 7.13 — Super Admin platform institution-management API contracts.

Security invariants baked into these schemas:

* ``extra="forbid"`` on every request model — a client can NEVER inject
  ``institution_id``, ``organization_id``, ``role``, ``scope_type``,
  ``scope_id``, ``status`` lifecycle transitions, or any other
  authorization-control field. The institution id arrives ONLY as a validated
  path parameter resolved server-side, and the acting actor is derived from the
  verified JWT, never from the body.
* ``status`` is deliberately ABSENT from the update request. Lifecycle
  transitions (active <-> suspended) are dedicated, separately audited
  endpoints, so a generic field update can never silently suspend or reactivate
  a tenant.
* Institution codes are normalized and validated server-side to a
  URL-safe, deterministic uppercase form. The client never decides casing.
* Responses are explicit projections. Raw database rows are never returned, so
  internal columns (organization linkage, contact details, join codes,
  credentials, any student data) cannot leak through the platform boundary.
"""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# The public routing identifier. Deliberately narrow: letters and digits, with
# internal hyphens/underscores. No whitespace, no slashes, no percent signs, no
# unicode. This keeps /u/{code}, /u/{code}/ai and /public-chat/{code} safe and
# predictable, and matches the frontend route guard exactly.
INSTITUTION_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")

# CSS hex colour, used only as an optional branding value.
_HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Branding logo must be an absolute http(s) URL. Rejecting anything else keeps
# javascript:/data: URLs out of the public gateway's <img src> binding.
_LOGO_URL_PATTERN = re.compile(r"^https?://[^\s]+$")

MAX_NAME_LENGTH = 200
MAX_BRANDING_TEXT_LENGTH = 300


def _normalized_code(value: str) -> str:
    """Normalize a supplied institution code to its canonical stored form.

    Deterministic and total: strip surrounding whitespace, uppercase, then
    validate. A blank or malformed code is rejected here rather than reaching
    the database, so no code with whitespace or special characters can ever be
    persisted as a routing identifier.
    """
    candidate = (value or "").strip().upper()
    if not INSTITUTION_CODE_PATTERN.fullmatch(candidate):
        raise ValueError(
            "must be 2-32 characters using letters, digits, hyphens or underscores"
        )
    return candidate


def _not_blank(value: str) -> str:
    stripped = (value or "").strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


def _optional_blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class InstitutionBrandingFields(BaseModel):
    """Optional branding fields shared by create and update.

    Every field is optional: branding is never mandatory for institution
    creation. Absent values stay NULL in the database and the public gateway
    keeps its neutral local defaults.
    """

    display_name: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, max_length=7)
    secondary_color: str | None = Field(default=None, max_length=7)
    welcome_message: str | None = Field(
        default=None, max_length=MAX_BRANDING_TEXT_LENGTH
    )

    @field_validator("display_name")
    @classmethod
    def _display_name_not_blank(cls, v: str | None) -> str | None:
        return None if v is None else _not_blank(v)

    @field_validator("logo_url")
    @classmethod
    def _logo_url_absolute_http(cls, v: str | None) -> str | None:
        if v is None:
            return None
        candidate = v.strip()
        if not candidate:
            return None
        if not _LOGO_URL_PATTERN.fullmatch(candidate):
            raise ValueError("must be an absolute http or https URL")
        return candidate

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def _color_is_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        candidate = v.strip()
        if not candidate:
            return None
        if not _HEX_COLOR_PATTERN.fullmatch(candidate):
            raise ValueError("must be a CSS hex colour such as #0F172A")
class InstitutionContactFields(BaseModel):
    """Optional public contact details, validated and trimmed."""

    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)

    @field_validator("address", "city", "country")
    @classmethod
    def _contact_blank_to_none(cls, v: str | None) -> str | None:
        return _optional_blank_to_none(v)


class InstitutionCreateRequest(InstitutionBrandingFields, InstitutionContactFields):
    """Super Admin institution creation payload.

    Only ``name`` and ``code`` are required. Branding is optional and is
    validated here rather than trusted, so a stored logo/colour can never be a
    script or style injection vector.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    code: str = Field(min_length=2, max_length=32)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("code")
    @classmethod
    def _code_normalized(cls, v: str) -> str:
        return _normalized_code(v)


class InstitutionUpdateRequest(InstitutionBrandingFields, InstitutionContactFields):
    """Super Admin institution configuration update.

    Partial by design: every field is optional and only the fields actually
    supplied are written. ``status`` is intentionally not present — lifecycle
    changes go through the dedicated, separately audited suspend/activate
    endpoints. ``institution_id`` and ``organization_id`` are structurally
    unchangeable, so an update can never reassign existing tenant data.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    code: str | None = Field(default=None, min_length=2, max_length=32)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str | None) -> str | None:
        return None if v is None else _not_blank(v)

    @field_validator("code")
    @classmethod
    def _code_normalized(cls, v: str | None) -> str | None:
        return None if v is None else _normalized_code(v)


class AdminAssignmentRequest(BaseModel):
    """Assign an EXISTING account as University Admin of one institution.

    This is a controlled *assignment* flow, not account creation. It carries no
    password and no credential material of any kind, so there is nothing
    sensitive to leak and no unsafe Auth provisioning path. The account must
    already exist in ``public.users`` (created through the established
    registration mechanisms); account creation for platform-provisioned admins
    is documented as a follow-up phase.

    The requested role is NOT accepted from the client. This endpoint grants
    exactly one fixed, institution-scoped role (``admin``) and can never be used
    to grant ``super_admin`` or any platform scope.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _email_normalized(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class InstitutionAdminView(BaseModel):
    """Safe projection of one institution admin assignment.

    Exposes only the account's opaque user id and email plus the granted
    institution scope. Never a name, student record, token or credential.
    """

    user_id: UUID
    email: str
    institution_id: UUID
    scope: Literal["institution"] = "institution"


class InstitutionAdminAssignmentResponse(BaseModel):
    """Result of assigning a University Admin to an institution."""

    institution_id: UUID
    assigned: bool
    already_assigned: bool
    admin: InstitutionAdminView


class InstitutionSummary(BaseModel):
    """Safe list projection for the Super Admin institution table.

    Only platform metadata: identity, public routing code, lifecycle status and
    the number of assigned admins. No student information, no academic records,
    no documents, no credentials.
    """

    id: UUID
    code: str
    name: str
    status: Literal["pending", "active", "suspended", "rejected"]
    is_active: bool
    admin_count: int


class InstitutionListResponse(BaseModel):
    """Explicit envelope for the institution list."""

    institutions: list[InstitutionSummary]


class InstitutionDetailResponse(BaseModel):
    """Safe institution detail projection.

    Contains identity, routing code, lifecycle status and optional branding
    only. Internal organization linkage, contact details, join codes and all
    tenant-owned data are intentionally omitted.
    """

    id: UUID
    code: str
    name: str
    display_name: str | None
    status: Literal["pending", "active", "suspended", "rejected"]
    is_active: bool
    logo_url: str | None
    primary_color: str | None
    secondary_color: str | None
    welcome_message: str | None
    created_at: str | None
    updated_at: str | None
    admin_count: int


class InstitutionLifecycleResponse(BaseModel):
    """Result of a suspend/activate lifecycle transition.

    States explicitly what suspension does and does not do: existing data is
    retained and no accounts are revoked. Kept separate from the detail
    projection so the UI can render an accurate confirmation.
    """

    id: UUID
    code: str
    name: str
    status: Literal["active", "suspended"]
    is_active: bool
    already_applied: bool
    message: str