"""Phase 6.7 — Attendance repository.

Scoped database access for the existing ``student_attendance`` table (Phase
Admin-1) hardened by the Phase 6.7 migration (server-derived
``institution_id``, ``updated_at``, and the tenant/academic-context guard
trigger).

All functions follow the project repository convention: the first argument is
an already-created Supabase ``Client`` (service-role client in production).

The attendance read projection is shared with
``app.repositories.admin_academics`` so the student self-service and the
admin management paths return identical row shapes.
"""

from uuid import UUID

from supabase import Client

from app.repositories import admin_academics as academics_repo

# Shared read projection (includes institution_id / updated_at since Phase 6.7).
STUDENT_ATTENDANCE_COLUMNS = academics_repo.STUDENT_ATTENDANCE_COLUMNS

# Section -> course_offering -> course -> department context projection used
# for academic-context / tenant validation of attendance rows.
_SECTION_CONTEXT_COLUMNS = (
    "section_id, code, "
    "course_offerings(course_id, academic_year_id, semester_id, program_id, "
    "courses(department_id, departments(institution_id)))"
)


def get_attendance_row(client: Client, attendance_id: UUID | str) -> dict | None:
    """Return one attendance row, or None when it does not exist."""
    response = (
        client.table("student_attendance")
        .select(STUDENT_ATTENDANCE_COLUMNS)
        .eq("student_attendance_id", str(attendance_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_context(
    client: Client, student_id: UUID | str
) -> dict | None:
    """Return the student's tenant anchor (student_id / institution_id /
    program_id), or None when the student does not exist."""
    response = (
        client.table("students")
        .select("student_id, institution_id, program_id")
        .eq("student_id", str(student_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_section_academic_context(
    client: Client, section_id: UUID | str
) -> dict | None:
    """Return the section's academic context, flattened:
    section_id, section_code, academic_year_id, semester_id, program_id,
    course_id, institution_id. Returns None for an unknown section or when
    the academic chain (offering/course/department) cannot be resolved.
    """
    response = (
        client.table("sections")
        .select(_SECTION_CONTEXT_COLUMNS)
        .eq("section_id", str(section_id))
        .maybe_single()
        .execute()
    )
    if response.data is None:
        return None
    row = response.data
    offering = row.get("course_offerings") or {}
    course = offering.get("courses") or {}
    department = course.get("departments") or {}
    return {
        "section_id": row.get("section_id"),
        "section_code": row.get("code"),
        "academic_year_id": offering.get("academic_year_id"),
        "semester_id": offering.get("semester_id"),
        "program_id": offering.get("program_id"),
        "course_id": offering.get("course_id"),
        "institution_id": department.get("institution_id"),
    }


def insert_attendance(client: Client, row: dict) -> dict:
    """Insert one attendance row and return the stored row.

    The caller is responsible for mapping database errors (duplicate unique
    keys, FK violations, guard-trigger rejections) to business errors.
    """
    response = client.table("student_attendance").insert(row).execute()
    return response.data[0]


def update_attendance_row(
    client: Client, attendance_id: UUID | str, fields: dict
) -> dict | None:
    """Update a subset of fields on one attendance row.

    Ownership fields (student_id, section_id, academic_year_id, semester_id,
    institution_id) are deliberately NOT updatable here; the Phase 6.7 guard
    trigger enforces the same rule at the database level. Returns the updated
    row, or None when the row disappeared between lookup and update.
    """
    response = (
        client.table("student_attendance")
        .update(fields)
        .eq("student_attendance_id", str(attendance_id))
        .execute()
    )
    return response.data[0] if response.data else None


def delete_attendance_row(client: Client, attendance_id: UUID | str) -> None:
    """Hard-delete one attendance row (Phase Admin-1 policy; the project does
    not use soft-delete infrastructure for attendance)."""
    (
        client.table("student_attendance")
        .delete()
        .eq("student_attendance_id", str(attendance_id))
        .execute()
    )


def list_attendance(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """List attendance rows for one student, most recent day first."""
    return academics_repo.list_student_attendance(
        client,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )