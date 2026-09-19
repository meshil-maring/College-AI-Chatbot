"""Student self-service API (Phase Admin-3).

All "me" endpoints authenticate with the existing ``get_current_user``
dependency. The student identity is resolved server-side from the
authenticated JWT (users.user_id → students.user_id); the client can never
supply another student's id.

Tenant isolation: the authenticated user's tenant (institution_id, resolved
from their students profile) must match the tenant of the student profile
whose data is returned — defence-in-depth against a stale/moved profile.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import assert_tenant_object, get_current_user
from app.schemas.student_profile import StudentAcademicProfile
from app.services import student_academic_profile as academic_profile_service
from app.services import student_data

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me/profile")
def my_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the authenticated student's own profile."""
    student = student_data.get_own_profile(UUID(current_user["user_id"]))
    assert_tenant_object(current_user, student.get("institution_id"))
    return student


@router.get("/me/academic-profile", response_model=StudentAcademicProfile)
def my_academic_profile(
    current_user: dict = Depends(get_current_user),
) -> StudentAcademicProfile:
    """Return the authenticated student's reusable academic profile.

    Phase 6.14.1: student-facing projection (no internal database
    identifiers). Identity and tenant are resolved server-side from the
    authenticated JWT via ``get_current_user``; the endpoint accepts NO
    identity parameters, so client-supplied ``student_id`` / ``user_id`` /
    ``institution_id`` / email / register-number / roll-number values can
    never override the authenticated identity (extra query/body fields are
    rejected with 422).
    """
    return academic_profile_service.get_academic_profile(current_user)


@router.get("/me/results")
def my_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published result summaries."""
    return student_data.get_own_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/results/{result_id}")
def my_result(
    result_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return ONE of the authenticated student's own published result
    summaries with its per-course grade rows (Phase 6.8).

    Identity is resolved server-side from the JWT; a missing, foreign, or
    unpublished result always yields the same 404 RESULT_NOT_FOUND so the
    endpoint cannot be used to enumerate other students' results.
    """
    result = student_data.get_own_result(UUID(current_user["user_id"]), result_id)
    assert_tenant_object(current_user, result.get("institution_id"))
    return result


@router.get("/me/test-results")
def my_test_results(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own published test scores."""
    return student_data.get_own_test_results(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )


@router.get("/me/attendance")
def my_attendance(
    academic_year_id: UUID | None = None,
    semester_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    """Return the authenticated student's own attendance records."""
    return student_data.get_own_attendance(
        UUID(current_user["user_id"]),
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
    )
