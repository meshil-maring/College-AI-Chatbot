"""Canonical student context resolution for Phase 6.9.

Provides a single, reliable way to resolve the authenticated student's context
from the Supabase Auth JWT through the identity chain:

    Supabase Auth JWT
        -> auth_user_id (JWT "sub" claim)
        -> public.users.auth_user_id
        -> public.users.user_id
        -> students.user_id
        -> students.student_id
        -> students.institution_id

Identity is ALWAYS derived server-side from the authenticated JWT.
The client can never supply student_id, user_id, or institution_id
as trusted identity fields for /students/me/* operations.

Eligibility:
    A student may access protected academic data only when ALL of:
    - Has an authenticated JWT
    - Has a student profile (students row exists)
    - approval_status == "approved"
    - is_active == True
    - institution.is_active == True

Returns:
    - No profile: 404 STUDENT_PROFILE_NOT_FOUND
    - Not approved/inactive: 403 FORBIDDEN
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo


CONTEXT_FIELDS = (
    "student_id",
    "user_id",
    "auth_user_id",
    "institution_id",
    "student_number",
    "email",
    "approval_status",
    "is_active",
    "status",
)


def get_student_context(current_user: dict[str, Any]) -> dict[str, Any]:
    """Resolve the canonical student context for the authenticated user.

    Args:
        current_user: The dict returned by get_current_user().

    Returns:
        A dict with the student's canonical context fields.

    Raises:
        AppError 404 STUDENT_PROFILE_NOT_FOUND: when no student profile.
        AppError 403 FORBIDDEN: when not approved or inactive.
    """
    user_id = current_user.get("user_id")
    auth_user_id = current_user.get("auth_user_id")

    if not user_id:
        raise AppError(
            "Invalid authenticated user context",
            status_code=400,
            code="INVALID_USER_CONTEXT",
        )

    db = get_admin_client()
    # Phase 6.22 (defect fix): the eligibility guard below reads
    # ``approval_status``, which the locked ``STUDENT_COLUMNS`` projection used
    # by ``get_student_by_user_id`` does not carry — so EVERY student was
    # rejected with 403 STUDENT_NOT_APPROVED here. The approval-relevant
    # projection supplies the real approval state without changing any existing
    # projection or weakening the guard.
    student = academics_repo.get_student_approval_row_by_user_id(db, str(user_id))

    if student is None:
        raise AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        )

    _assert_student_eligible(student, db)

    context = {
        "student_id": student["student_id"],
        "user_id": student["user_id"],
        "auth_user_id": auth_user_id,
        "institution_id": student["institution_id"],
        "student_number": student.get("student_number"),
        "email": student.get("email"),
        "approval_status": student.get("approval_status"),
        "is_active": student.get("is_active", True),
        "status": student.get("status"),
    }

    return context


def _assert_student_eligible(student: dict[str, Any], db) -> None:
    """Verify the student meets eligibility requirements for data access.

    Eligibility requires:
        - approval_status == "approved"
        - is_active == True
        - institution.is_active == True
    """
    approval_status = student.get("approval_status")
    is_active = student.get("is_active", True)
    institution_id = student.get("institution_id")

    if approval_status != "approved":
        raise AppError(
            "Student account is not approved",
            status_code=403,
            code="STUDENT_NOT_APPROVED",
        )

    if not is_active:
        raise AppError(
            "Student account is inactive",
            status_code=403,
            code="STUDENT_INACTIVE",
        )

    if institution_id is not None:
        from app.services.student_auth import _assert_institution_active

        _assert_institution_active(db, UUID(str(institution_id)))


def assert_student_context_tenant(
    current_user: dict[str, Any], student_context: dict[str, Any]
) -> None:
    """Defense-in-depth: assert the student context's institution matches
    the current user's resolved tenant.
    """
    from app.core.security import assert_tenant_object

    institution_id = student_context.get("institution_id")
    assert_tenant_object(current_user, institution_id)
