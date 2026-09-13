"""Phase 6.8 — Results repository.

Scoped database access over the EXISTING result tables created in Phase
Admin-1 (``test_results``, ``student_results``, ``student_result_items``),
hardened by the Phase 6.8 migration (server-derived ``institution_id``, score
integrity CHECKs, and tenant/academic-context guard triggers).

All functions follow the project repository convention: the first argument is
an already-created Supabase ``Client`` (service-role client in production).
Read projections extend the Phase Admin-2 projections in
``app.repositories.admin_academics`` with the Phase 6.8 ``institution_id``
column, so the admin management and student self-service paths return
identical row shapes without touching the locked Admin-2 module.

Academic-context lookups reuse the Phase 6.7 attendance repository helpers
where the same chain (student anchor, section -> offering -> course ->
department) is already implemented.
"""

from uuid import UUID

from supabase import Client

from app.repositories import admin_academics as academics_repo

# Phase 6.8 projections: the Admin-2 read projections plus the server-derived
# tenant column added by the Phase 6.8 migration.
TEST_RESULT_COLUMNS = academics_repo.TEST_RESULT_COLUMNS + ", institution_id"
STUDENT_RESULT_COLUMNS = academics_repo.STUDENT_RESULT_COLUMNS + ", institution_id"
STUDENT_RESULT_ITEM_COLUMNS = academics_repo.STUDENT_RESULT_ITEM_COLUMNS


def get_student_context(client: Client, student_id: UUID | str) -> dict | None:
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


def get_academic_year_context(client: Client, academic_year_id: UUID | str) -> dict | None:
    """Return the academic year's tenant anchor, or None when it does not
    exist (``academic_years.institution_id`` is NOT NULL in the schema)."""
    response = (
        client.table("academic_years")
        .select("academic_year_id, institution_id")
        .eq("academic_year_id", str(academic_year_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_semester_context(client: Client, semester_id: UUID | str) -> dict | None:
    """Return the semester's owning academic year, or None when the semester
    does not exist (used to reject semester/academic-year mismatches)."""
    response = (
        client.table("semesters")
        .select("semester_id, academic_year_id")
        .eq("semester_id", str(semester_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_course_institution(client: Client, course_id: UUID | str) -> UUID | str | None:
    """Resolve the course's institution via courses -> departments.

    Returns None for an unknown course or a broken course/department chain
    (callers fail closed on None).
    """
    response = (
        client.table("courses")
        .select("course_id, departments(institution_id)")
        .eq("course_id", str(course_id))
        .maybe_single()
        .execute()
    )
    row = response.data
    if row is None:
        return None
    department = row.get("departments") or {}
    return department.get("institution_id")


def get_program_institution(client: Client, program_id: UUID | str) -> UUID | str | None:
    """Resolve the program's institution via programs -> departments.

    Returns None for an unknown program or a broken program/department chain
    (callers fail closed on None).
    """
    response = (
        client.table("programs")
        .select("program_id, departments(institution_id)")
        .eq("program_id", str(program_id))
        .maybe_single()
        .execute()
    )
    row = response.data
    if row is None:
        return None
    department = row.get("departments") or {}
    return department.get("institution_id")


# ============================================================================
# Test results
# ============================================================================


def get_test_result_row(client: Client, test_result_id: UUID | str) -> dict | None:
    """Return one test result row (Phase 6.8 projection), or None."""
    response = (
        client.table("test_results")
        .select(TEST_RESULT_COLUMNS)
        .eq("test_result_id", str(test_result_id))
        .maybe_single()
        .execute()
    )
    return response.data


def insert_test_result(client: Client, row: dict) -> dict:
    """Insert one test result row and return the stored row.

    The caller is responsible for mapping database errors (duplicate unique
    keys, FK violations, guard-trigger rejections) to business errors.
    """
    response = client.table("test_results").insert(row).execute()
    return response.data[0]


def update_test_result_row(
    client: Client, test_result_id: UUID | str, fields: dict
) -> dict | None:
    """Update a subset of fields on one test result row.

    Ownership fields (student_id, course_id, academic_year_id, semester_id,
    institution_id) are deliberately NOT updatable here; the Phase 6.8 guard
    trigger enforces the same rule at the database level. Returns the updated
    row, or None when the row disappeared between lookup and update.
    """
    response = (
        client.table("test_results")
        .update(fields)
        .eq("test_result_id", str(test_result_id))
        .execute()
    )
    return response.data[0] if response.data else None


def delete_test_result_row(client: Client, test_result_id: UUID | str) -> None:
    """Hard-delete one test result row (Phase Admin-1 policy; the project
    does not use soft-delete infrastructure for student academic rows)."""
    (
        client.table("test_results")
        .delete()
        .eq("test_result_id", str(test_result_id))
        .execute()
    )


def list_test_results(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List per-test scores for a student (Admin-2 projection reused)."""
    return academics_repo.list_test_results(
        client,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        limit=limit,
    )


# ============================================================================
# Student results (consolidated per-semester summaries)
# ============================================================================


def get_student_result_row(client: Client, student_result_id: UUID | str) -> dict | None:
    """Return one result summary row (Phase 6.8 projection), or None."""
    response = (
        client.table("student_results")
        .select(STUDENT_RESULT_COLUMNS)
        .eq("student_result_id", str(student_result_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_result_with_items(
    client: Client, student_result_id: UUID | str
) -> dict | None:
    """Return one result summary with its per-course grade rows (Phase 6.8
    projection so reads include the tenant column)."""
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


def insert_student_result(client: Client, row: dict) -> dict:
    """Insert one result summary row and return the stored row.

    The caller is responsible for mapping database errors (duplicate unique
    keys, FK violations, guard-trigger rejections) to business errors.
    """
    response = client.table("student_results").insert(row).execute()
    return response.data[0]


def insert_student_result_items(client: Client, rows: list[dict]) -> list[dict]:
    """Insert per-course grade rows for one result summary."""
    response = client.table("student_result_items").insert(rows).execute()
    return response.data


def update_student_result_row(
    client: Client, student_result_id: UUID | str, fields: dict
) -> dict | None:
    """Update a subset of fields on one result summary row.

    Ownership fields (student_id, academic_year_id, semester_id, program_id,
    institution_id) are deliberately NOT updatable here; the Phase 6.8 guard
    trigger enforces the same rule at the database level. Returns the updated
    row, or None when the row disappeared between lookup and update.
    """
    response = (
        client.table("student_results")
        .update(fields)
        .eq("student_result_id", str(student_result_id))
        .execute()
    )
    return response.data[0] if response.data else None


def delete_student_result(client: Client, student_result_id: UUID | str) -> None:
    """Hard-delete one result summary and its per-course rows (FK CASCADE
    already removes the items; the explicit item delete keeps the operation
    deterministic for repositories that bypass the constraint)."""
    (
        client.table("student_result_items")
        .delete()
        .eq("student_result_id", str(student_result_id))
        .execute()
    )
    (
        client.table("student_results")
        .delete()
        .eq("student_result_id", str(student_result_id))
        .execute()
    )


def list_student_results(
    client: Client,
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
) -> list[dict]:
    """List result summaries for a student (Admin-2 projection reused)."""
    return academics_repo.list_student_results(
        client,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
    )