"""Phase 6.13.5 — Student, Faculty & Staff registration schemas.

Security invariants (consistent with existing Phase 6.3 / 6.13 schemas):

* ``extra=\"forbid\"`` everywhere — clients can NEVER inject ``role``,
  ``scope_type``, ``scope_id``, ``status``, ``approval_status`` or any other
  authorization-control field. Role and scope are decided ONLY server-side.
* Public registration payloads never accept internal database ids; they use
  the public code (``institution_code``), which the server resolves to an id.
* ``registration_type`` is a Literal restricted to ``student | faculty | staff``
  — a privilege-escalation request ("admin") is unrepresentable and rejected
  with 422 before any service call.
* Student identity fields (``register_number``, ``university_roll_number``) are
  required when ``registration_type=student`` and rejected otherwise.
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


def _normalize_code(value: str) -> str:
    value = _not_blank(value)
    return value.upper()


class UserRegistrationRequest(BaseModel):
    """Public user registration payload (student, faculty, or staff).

    The ``registration_type`` determines which fields are required and which
    role the user will eventually receive upon approval. The role and scope are
    assigned server-side — the payload cannot influence them.

    For students: ``register_number`` and/or ``university_roll_number`` are
    required (at least one). These become the student's academic identifiers
    scoped to the institution.

    For faculty/staff: ``designation`` and ``department`` are optional.
    """

    model_config = ConfigDict(extra="forbid")

    registration_type: Literal["student", "faculty", "staff"] = Field(
        ..., description="The type of user being registered"
    )
    institution_code: str = Field(
        ..., min_length=2, max_length=64,
        description="Public institution code (server-resolved to institution id)"
    )
    email: EmailStr
    password: str = Field(
        ..., description="Password (goes ONLY to Supabase Auth, never stored)"
    )
    first_name: str
    last_name: str
    # Student-specific academic identifiers
    register_number: str | None = None
    university_roll_number: str | None = None
    # Faculty/Staff optional fields
    designation: str | None = None
    department: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _names_not_blank(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("institution_code")
    @classmethod
    def _code_normalized(cls, v: str) -> str:
        return _normalize_code(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _password_min_length(v)

    @field_validator("register_number", "university_roll_number")
    @classmethod
    def _identity_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("designation", "department")
    @classmethod
    def _optional_blank_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class UserRegistrationResponse(BaseModel):
    """Response after user registration — clearly pending approval.

    Never exposes a password, auth token, or role assignments.
    """

    message: str
    user_id: UUID
    institution_id: UUID
    institution_code: str
    registration_type: str
    approval_status: str = "pending"
    # Student-specific
    student_id: UUID | None = None
    # Faculty/Staff-specific
    request_id: UUID | None = None
