"""Student self-service API (Phase Admin-3).

All "me" endpoints authenticate with the existing ``get_current_user``
dependency. The student identity is resolved server-side from the
authenticated JWT (users.user_id → students.user_id); the client can never
supply another student's id.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.services import student_data

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me/profile")
def my_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """Return the authenticated student's own profile."""
    return student_data.get_own_profile(UUID(current_user["user_id"]))


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
