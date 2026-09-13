"""Phase 6.5 — Student authentication schemas.

Student login accepts an ``identifier`` (email / register number / university
roll number) plus a ``password``. The password is forwarded to Supabase Auth
(GoTrue) and is never stored, hashed, or compared by this application.

For email login: ``identifier`` is the email, no institution context needed
(email is globally unique per public.users).

For academic identifier login (register_number / university_roll_number):
``institution_code`` is REQUIRED because academic identifiers are institution-
scoped (Phase 6.2). The existing ``institutions.code`` column provides the
public institution identifier.

Security: ``extra="forbid"`` so clients cannot inject ``role``,
``user_id``, ``student_id``, ``institution_id``, ``approval_status``, or
``auth_user_id`` as authentication-control fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.errors import AppError


class StudentLoginRequest(BaseModel):
    """Public student login payload.

    ``identifier`` may be an email address or an academic identifier
    (register_number / university_roll_number). ``password`` is forwarded
    directly to Supabase Auth and is never inspected or stored by this app.

    For email login: only ``identifier`` (email) and ``password`` are used.

    For academic identifier login: ``institution_code`` is REQUIRED because
    academic identifiers are institution-scoped (Phase 6.2). The existing
    ``institutions.code`` column provides the public institution identifier.
    """

    model_config = ConfigDict(extra="forbid")

    identifier: str
    password: str
    institution_code: str | None = None

    @field_validator("identifier")
    @classmethod
    def identifier_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("identifier must not be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("password must not be empty")
        return v

    @field_validator("institution_code")
    @classmethod
    def institution_code_clean(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("institution_code must not be empty")
        return v


def _validate_login_request(body: StudentLoginRequest) -> None:
    """Validate login request consistency.

    Academic identifier login requires institution_code.
    Email login ignores institution_code (if provided).
    """
    if not _is_email(body.identifier):
        # Academic identifier login requires institution_code
        if body.institution_code is None or body.institution_code.strip() == "":
            raise AppError(
                message="institution_code is required for academic identifier login",
                status_code=422,
                code="VALIDATION_ERROR",
            )


def _is_email(value: str) -> bool:
    """Heuristic email detection for choosing the lookup path."""
    return "@" in value and "." in value.split("@")[-1]


class StudentLoginResponse(BaseModel):
    """Successful student login response — reuses the existing auth contract
    (access_token / message / user) so the frontend treats it like any other
    Supabase Auth login.
    """

    access_token: str
    message: str
    user: dict


class StudentAuthServiceError(AppError):
    """Internal service-layer auth failure — normalised to safe client errors
    at the API boundary so account-existence is never leaked.
    """

    pass