"""Phase 6.5 - Student authentication service.

Authenticates a student using Supabase Auth as the single credential authority.
Supports two login modes:

1. Email login (no institution context):
   email + password -> Supabase Auth sign-in directly

2. Academic identifier login (institution_code REQUIRED):
   institution_code + register_number + password
   institution_code + university_roll_number + password

Architecture (locked phases preserved):

    auth.users (Supabase GoTrue)
        |  auth_user_id
    public.users
        |  user_id
    students
        |  institution_id
    institutions (code column is the public identifier)

The application NEVER stores or compares passwords. The password is handed to
GoTrue and is never logged, echoed, or persisted anywhere in this service.

Phase 6.2 (LOCKED) established institution-scoped uniqueness for
register_number and university_roll_number. Therefore academic identifier
login REQUIRES institution_code to disambiguate. Email is globally unique
per public.users and does not require institution context.
"""

from __future__ import annotations

import logging
from uuid import UUID

from supabase import Client
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.db.supabase import create_supabase_client, get_admin_client
from app.repositories import admin_academics as academics_repo

logger = logging.getLogger(__name__)


class SafeAuthFailure(AppError):
    """Generic authentication failure that does NOT disclose account state."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid identifier or password",
            status_code=401,
            code="INVALID_CREDENTIALS",
        )


def _is_email(value: str) -> bool:
    """Heuristic email detection for choosing the lookup path."""
    return "@" in value and "." in value.split("@")[-1]


def _find_institution_by_code(db: Client, code: str) -> dict | None:
    """Find an institution by its public code (e.g., 'GIT').

    Returns the institution row or None. The code is the public-facing
    identifier; the internal UUID is never exposed to the client.
    """
    response = (
        db.table("institutions")
        .select("institution_id, name, code, is_active")
        .eq("code", code.strip().upper())
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data if response.data else None


def _resolve_by_email(
    db: Client, email: str
) -> tuple[str, UUID, dict] | None:
    """Email is globally unique per public.users - find the linked student."""
    student = academics_repo.get_student_by_email_global(db, email)
    if student is None:
        return None
    inst_id = student["institution_id"]
    return (student["email"].lower(), UUID(str(inst_id)), student)


def _resolve_academic_id_with_context(
    db: Client,
    institution_code: str,
    identifier: str,
) -> tuple[str, UUID, dict] | None:
    """Resolve academic identifier WITH institution context.

    Uses the institution_code to scope the lookup to a single institution,
    avoiding cross-tenant ambiguity.
    """
    institution = _find_institution_by_code(db, institution_code)
    if institution is None:
        logger.info("Login blocked: institution_code not found")
        return None

    institution_id = UUID(str(institution["institution_id"]))

    # Lookup academic identifier SCOPED to this institution
    by_register = academics_repo.get_student_by_register_number(
        db, institution_id, identifier
    )
    by_roll = academics_repo.get_student_by_university_roll_number(
        db, institution_id, identifier
    )

    if by_register is None and by_roll is None:
        return None

    # Same student matched both fields (or one field matched)
    if by_register is not None and by_roll is not None:
        if by_register["student_id"] != by_roll["student_id"]:
            logger.warning("Ambiguous academic identifier within institution: %s", identifier)
            raise SafeAuthFailure()
        student = by_register
    elif by_register is not None:
        student = by_register
    else:
        student = by_roll

    return (student["email"].lower(), institution_id, student)


def _resolve_identity(
    db: Client,
    identifier: str,
    institution_code: str | None = None,
) -> tuple[str, UUID, dict] | None:
    """Resolve an identifier to exactly one (email, institution_id, student).

    For email: no institution context needed (globally unique).
    For academic identifiers: institution_code is REQUIRED to scope the lookup.

    Returns None when no student matches. Raises SafeAuthFailure on ambiguity.
    """
    if _is_email(identifier):
        # Email login - no institution context needed
        return _resolve_by_email(db, identifier.lower())

    # Academic identifier login - institution_code is REQUIRED
    if institution_code is None:
        logger.info("Login blocked: academic identifier without institution_code")
        return None

    return _resolve_academic_id_with_context(db, institution_code, identifier)


def _assert_approved(student: dict) -> None:
    """Only approval_status='approved' students may authenticate."""
    if student.get("approval_status") != "approved":
        raise SafeAuthFailure()


def _assert_student_active(student: dict) -> None:
    """Inactive students cannot authenticate."""
    if not student.get("is_active", True):
        raise SafeAuthFailure()


def _get_institution(db: Client, institution_id: UUID | str) -> dict | None:
    """Return institution row or None."""
    response = (
        db.table("institutions")
        .select("institution_id, name, code, is_active")
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data if response.data else None


def _assert_institution_active(db: Client, institution_id: UUID) -> None:
    """Inactive institutions cannot authenticate."""
    institution = _get_institution(db, institution_id)
    if institution is None or not institution.get("is_active", True):
        raise SafeAuthFailure()


def _supabase_sign_in(email: str, password: str) -> dict:
    """Delegate to Supabase Auth (GoTrue)."""
    client = create_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthApiError:
        raise SafeAuthFailure()
    if response.session is None or response.session.access_token is None:
        raise SafeAuthFailure()
    return {
        "access_token": response.session.access_token,
        "user": {"id": response.user.id, "email": response.user.email},
    }


def authenticate_student(identifier: str, password: str, institution_code: str | None = None) -> dict:
    """Authenticate a student and return a login response."""
    if not password:
        raise SafeAuthFailure()

    db = get_admin_client()
    resolved = _resolve_identity(db, identifier, institution_code)
    if resolved is None:
        raise SafeAuthFailure()

    email, institution_id, student = resolved
    _assert_approved(student)
    _assert_student_active(student)
    _assert_institution_active(db, institution_id)
    return _supabase_sign_in(email, password)