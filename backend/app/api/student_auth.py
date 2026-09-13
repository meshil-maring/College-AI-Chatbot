"""Phase 6.5 — Student authentication API.

Public student login endpoint supporting three identifier types:

    POST /api/v1/auth/student/login
        identifier: email | register_number | university_roll_number
        password: str

The password is forwarded to Supabase Auth (GoTrue) and is never stored,
hashed, or compared by this application. Supabase Auth remains the SINGLE
credential authority.

Security:
    * Request schema uses ``extra="forbid"`` — clients cannot inject
      ``role`` / ``user_id`` / ``student_id`` / ``institution_id`` /
      ``approval_status`` / ``auth_user_id`` as authentication-control fields.
    * Identifier resolution is deterministic and unambiguous — cross-tenant
      collisions fail safely.
    * Approval enforcement (Phase 6.4): only ``approval_status='approved'``
      students may authenticate.
    * Lifecycle enforcement: inactive students and inactive institutions are
      blocked.
    * Safe error responses — account existence, approval state, and lifecycle
      state are never disclosed to the client.
    * No role escalation — this endpoint does not grant roles.
    * Admin/staff credentials against this endpoint must NOT produce student
      sessions (they simply fail as invalid credentials).

Failure normalization:
    All authentication failures (unknown identifier, wrong password, pending /
    rejected student, inactive student/institution, ambiguous identity) are
    normalized to ``401 INVALID_CREDENTIALS`` so the client cannot enumerate
    accounts.
"""

from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.student_auth import (
    StudentAuthServiceError,
    StudentLoginRequest,
    StudentLoginResponse,
    _validate_login_request,
)
from app.services.student_auth import authenticate_student

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/student/login",
    status_code=200,
    response_model=StudentLoginResponse,
    summary="Student login (email / register number / university roll number)",
    description="""Authenticate as a student using an email or academic identifier plus password.

**Email login** (no institution context needed):
    identifier = email address
    password = password

**Academic identifier login** (institution_code REQUIRED):
    identifier = register_number OR university_roll_number
    institution_code = public institution code (e.g., 'GIT')
    password = password

The password is verified by Supabase Auth; this application never stores or
compares passwords. Academic identifiers are institution-scoped per Phase 6.2,
so institution_code is required to disambiguate.
""",
)
def student_login(body: StudentLoginRequest) -> StudentLoginResponse:
    """Authenticate a student and return a Supabase Auth session.

    The identifier may be an email address or an academic identifier
    (register_number / university_roll_number). For academic identifiers,
    institution_code is required to scope the lookup.

    The backend resolves the identifier to the student's email, validates
    approval + lifecycle state, and delegates credential verification to
    Supabase Auth.
    """
    # Validate request: academic identifier login requires institution_code
    _validate_login_request(body)

    try:
        result = authenticate_student(
            body.identifier,
            body.password,
            body.institution_code,
        )
    except StudentAuthServiceError as exc:
        # Normalise all service-layer auth failures to safe 401 responses.
        raise AppError(
            exc.message or "Invalid identifier or password",
            status_code=exc.status_code or 401,
            code=exc.code or "INVALID_CREDENTIALS",
        ) from exc

    return StudentLoginResponse(
        access_token=result["access_token"],
        message="Login successful.",
        user=result["user"],
    )