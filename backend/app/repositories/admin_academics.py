"""Read-oriented admin repositories over student academic data.

Phase Admin-2 — Backend Contracts & Repositories.

All functions take an already-created Supabase ``Client`` as their first
argument (service-role client in production), following the existing
repository convention in ``app.repositories``.

These functions only READ student academic tables (students, student_results,
student_result_items, test_results, student_attendance) created in Phase
Admin-1. Student academic data is never injected into the RAG pipeline.
"""

from uuid import UUID

from supabase import Client

STUDENT_COLUMNS = (
    "student_id, user_id, institution_id, student_number, program_id, "
    "academic_year_id, enrollment_date, expected_graduation_date, status, "
    "is_active, created_at, updated_at"
)

STUDENT_RESULT_COLUMNS = (
    "student_result_id, student_id, academic_year_id, semester_id, "
    "program_id, result_type, total_credits_earned, total_credits_max, "
    "sgpa, cgpa, status, issued_at"
)

STUDENT_RESULT_ITEM_COLUMNS = (
    "student_result_item_id, student_result_id, course_id, section_id, "
    "credits_earned, credits_max, grade_points, letter_grade, grade_value, "
    "status, created_at"
)

TEST_RESULT_COLUMNS = (
    "test_result_id, student_id, course_id, section_id, academic_year_id, "
    "semester_id, test_name, test_type, max_marks, scored_marks, percentage, "
    "letter_grade, conducted_at, status, created_at, updated_at"
)

STUDENT_ATTENDANCE_COLUMNS = (
    "student_attendance_id, student_id, section_id, academic_year_id, "
    "semester_id, date, status, notes, created_at"
)


# ============================================================================
# Students
# ============================================================================


def list_students(
    client: Client,
    institution_id: UUID | str,
    program_id: UUID | str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List student profiles for an institution, ordered by student number."""
    query = (
        client.table("students")
        .select(STUDENT_COLUMNS)
        .eq("institution_id", str(institution_id))
    )
    if program_id is not None:
        query = query.eq("program_id", str(program_id))
    if status is not None:
        query = query.eq("status", status)
    response = (
        query.order("student_number")
        .limit(limit)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def get_student(client: Client, student_id: UUID | str) -> dict | None:
    """Return one student profile, or None when it does not exist."""
    response = (
        client.table("students")
        .select(STUDENT_COLUMNS)
        .eq("student_id", str(student_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_by_user_id(client: Client, user_id: UUID | str) -> dict | None:
    """Return the student profile for a users.user_id, or None when absent."""
    response = (
        client.table("students")
        .select(STUDENT_COLUMNS)
        .eq("user_id", str(user_id))
        .maybe_single()
        .execute()
    )
    return response.data


# ============================================================================
# Student results
# ============================================================================


def list_student_results(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
) -> list[dict]:
    """List result summaries for a student, newest issued first."""
    query = (
        client.table("student_results")
        .select(STUDENT_RESULT_COLUMNS)
        .eq("student_id", str(student_id))
    )
    if academic_year_id is not None:
        query = query.eq("academic_year_id", str(academic_year_id))
    if semester_id is not None:
        query = query.eq("semester_id", str(semester_id))
    response = query.order("issued_at", desc=True).execute()
    return response.data


def get_student_result_with_items(
    client: Client,
    student_result_id: UUID | str,
) -> dict | None:
    """Return a result summary with its per-course grade rows."""
    response = (
        client.table("student_results")
        .select(
            f"{STUDENT_RESULT_COLUMNS}, "
            f"student_result_items({STUDENT_RESULT_ITEM_COLUMNS})"
        )
        .eq("student_result_id", str(student_result_id))
        .maybe_single()
        .execute()
    )
    return response.data


# ============================================================================
# Test results
# ============================================================================


def list_test_results(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List per-test scores for a student, newest conducted first."""
    query = (
        client.table("test_results")
        .select(TEST_RESULT_COLUMNS)
        .eq("student_id", str(student_id))
    )
    if academic_year_id is not None:
        query = query.eq("academic_year_id", str(academic_year_id))
    if semester_id is not None:
        query = query.eq("semester_id", str(semester_id))
    response = (
        query.order("conducted_at", desc=True).limit(limit).execute()
    )
    return response.data


# ============================================================================
# Attendance
# ============================================================================


def list_student_attendance(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """List attendance records for a student, most recent day first."""
    query = (
        client.table("student_attendance")
        .select(STUDENT_ATTENDANCE_COLUMNS)
        .eq("student_id", str(student_id))
    )
    if academic_year_id is not None:
        query = query.eq("academic_year_id", str(academic_year_id))
    if semester_id is not None:
        query = query.eq("semester_id", str(semester_id))
    if date_from is not None:
        query = query.gte("date", date_from)
    if date_to is not None:
        query = query.lte("date", date_to)
    response = query.order("date", desc=True).limit(limit).execute()
    return response.data