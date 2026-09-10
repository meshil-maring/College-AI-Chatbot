"""Student self-service data access (Phase Admin-3).

Every lookup resolves the student profile server-side from the authenticated
user id (derived from the Supabase JWT via ``get_current_user``). The client
can never supply another student's id: "me" endpoints are strictly scoped to
the caller's own profile, results, test results, and attendance.

Only published results are exposed to students; draft/withheld rows stay
admin-only. Attendance has no publication state and is returned as recorded.
"""

from uuid import UUID

from supabase import Client

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo


def get_own_student(
    user_id: UUID | str,
    client: Client | None = None,
) -> dict:
    """Resolve the student profile linked to the authenticated user id.

    Raises 404 when the account has no student profile — the client never
    chooses which student is queried.
    """
    db = client or get_admin_client()
    student = academics_repo.get_student_by_user_id(db, str(user_id))
    if student is None:
        raise AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        )
    return student


def get_own_profile(user_id: UUID | str, client: Client | None = None) -> dict:
    """Return the authenticated student's own profile."""
    return get_own_student(user_id, client=client)


def get_own_results(
    user_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Client | None = None,
) -> list[dict]:
    """Return the authenticated student's own published result summaries."""
    db = client or get_admin_client()
    student = get_own_student(user_id, client=db)
    rows = academics_repo.list_student_results(
        db,
        student["student_id"],
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )
    return [row for row in rows if row.get("status") == "published"]


def get_own_test_results(
    user_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Client | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return the authenticated student's own published test scores."""
    db = client or get_admin_client()
    student = get_own_student(user_id, client=db)
    rows = academics_repo.list_test_results(
        db,
        student["student_id"],
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        limit=limit,
    )
    return [row for row in rows if row.get("status") == "published"]


def get_own_attendance(
    user_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    client: Client | None = None,
    limit: int = 200,
) -> list[dict]:
    """Return the authenticated student's own attendance records."""
    db = client or get_admin_client()
    student = get_own_student(user_id, client=db)
    return academics_repo.list_student_attendance(
        db,
        student["student_id"],
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
