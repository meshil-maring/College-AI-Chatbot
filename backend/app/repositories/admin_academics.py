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

# Phase 6.2 identity-only projection used exclusively by the identity
# resolution functions below (email / register number / university roll
# number). Existing student/admin projections (STUDENT_COLUMNS) are unchanged
# for backward compatibility until the Phase 6.2 migration is applied to the
# remote database; the future student-authentication phase (6.5) consumes the
# identity projection.
STUDENT_IDENTITY_COLUMNS = (
    "student_id, user_id, institution_id, student_number, email, "
    "register_number, university_roll_number, approval_status, status, "
    "is_active"
)

# Phase 6.4 — approval-queue projection (minimal student info only).
# Never includes passwords/tokens/secrets: students rows carry no credentials.
STUDENT_APPROVAL_COLUMNS = (
    "student_id, user_id, institution_id, student_number, email, "
    "register_number, university_roll_number, approval_status, status, "
    "is_active, enrollment_date, created_at, updated_at"
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
    "student_attendance_id, student_id, institution_id, section_id, "
    "academic_year_id, semester_id, date, status, notes, created_at, updated_at"
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
# Student identity resolution (Phase 6.2 model support)
# ============================================================================
#
# Identity lookups are ALWAYS institution-scoped. Academic identifiers are
# assigned per institution (College A and College B may both use register
# number 1001), so an identifier value alone never identifies one student —
# resolution requires the institution_id tenant context (Phase 6.1 boundary).
# Email is additionally unique per institution; account-level login-email
# uniqueness remains owned by public.users.email + Supabase Auth.


def get_student_by_email(
    client: Client,
    institution_id: UUID | str,
    email: str,
) -> dict | None:
    """Resolve an institutional email to a student within an institution.

    Emails are stored lowercase/trimmed (enforced by students_email_check),
    so the lookup value is normalized the same way.
    """
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("email", str(email).strip().lower())
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_by_email_global(
    client: Client,
    email: str,
) -> dict | None:
    """Resolve an email to a student across ALL institutions.

    Used by authentication flows where the institution context is not yet known.
    Email is globally unique per public.users, so at most one student should match.
    """
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("email", str(email).strip().lower())
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_by_register_number(
    client: Client,
    institution_id: UUID | str,
    register_number: str,
) -> dict | None:
    """Resolve a register number to a student within an institution."""
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("register_number", str(register_number).strip())
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_by_register_number_global(
    client: Client,
    register_number: str,
) -> list[dict]:
    """Resolve a register number across ALL institutions.

    Returns all matching students (could be multiple at different institutions).
    Used by authentication to detect cross-tenant ambiguity.
    """
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("register_number", str(register_number).strip())
        .execute()
    )
    return response.data or []


def get_student_by_university_roll_number(
    client: Client,
    institution_id: UUID | str,
    university_roll_number: str,
) -> dict | None:
    """Resolve a university roll number to a student within an institution."""
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("university_roll_number", str(university_roll_number).strip())
        .maybe_single()
        .execute()
    )
    return response.data


def get_student_by_university_roll_number_global(
    client: Client,
    university_roll_number: str,
) -> list[dict]:
    """Resolve a university roll number across ALL institutions.

    Returns all matching students (could be multiple at different institutions).
    Used by authentication to detect cross-tenant ambiguity.
    """
    response = (
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("university_roll_number", str(university_roll_number).strip())
        .execute()
    )
    return response.data or []


def resolve_student_by_identifier(
    client: Client,
    institution_id: UUID | str,
    identifier: str,
) -> dict | None:
    """Resolve one identity value to a student within an institution.

    Tries, in order: institutional email, register number, university roll
    number. Returns the first matching student, or None when no identifier
    matches within the institution. This is the single entry point later
    phases (6.5 student authentication) will use to uniquely identify a
    student by any supported login identifier within their institution.
    """
    value = str(identifier).strip()
    if not value:
        return None

    lookups = (
        get_student_by_email,
        get_student_by_register_number,
        get_student_by_university_roll_number,
    )
    for lookup in lookups:
        student = lookup(client, institution_id, value)
        if student is not None:
            return student
    return None


# ============================================================================
# Student approval queue (Phase 6.4 model support)
# ============================================================================
#
# Approval reads/writes are ALWAYS institution-scoped (Phase 6.1 boundary):
# the caller's tenant (institution_id) is the ONLY tenant filter. No
# client-supplied institution_id, role, or approval_status ever acts as an
# authorization control — callers pass the already-resolved tenant in.
#
# The approval state machine is strict:
#     pending -> approved | rejected
# Any other transition is rejected with 409 (INVALID_TRANSITION / NOT_PENDING).


def list_pending_students(
    client: Client,
    institution_id: UUID | str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List pending-approval students, tenant-scoped or global.

    ``institution_id`` is the caller's ALREADY-RESOLVED tenant (never a
    client-supplied control). Passing ``None`` is the Phase 6.1
    platform-admin passthrough: the API layer only permits it for
    platform-level admins (no students profile). Tenant-bound callers always
    receive their own institution id from the endpoint.

    Minimal approval projection only (STUDENT_APPROVAL_COLUMNS) — no
    passwords/tokens/secrets exist on students rows and none are returned.
    Ordered by created_at (oldest request first) so reviewers see the queue.
    """
    query = client.table("students").select(STUDENT_APPROVAL_COLUMNS)
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    response = (
        query.eq("approval_status", "pending")
        .order("created_at")
        .limit(limit)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data


def get_student_for_approval(
    client: Client,
    student_id: UUID | str,
) -> dict | None:
    """Return one student row with the approval projection, or None."""
    response = (
        client.table("students")
        .select(STUDENT_APPROVAL_COLUMNS)
        .eq("student_id", str(student_id))
        .maybe_single()
        .execute()
    )
    return response.data


def set_student_approval_status(
    client: Client,
    student_id: UUID | str,
    institution_id: UUID | str,
    new_status: str,
) -> dict | None:
    """Conditionally transition one pending student to approved/rejected.

    Concurrency-safe: the UPDATE only matches while the row is still pending
    within the caller's tenant::

        UPDATE students SET approval_status = <new>
        WHERE student_id = X AND institution_id = <tenant>
          AND approval_status = 'pending'

    Returns the updated row, or None when no pending row matched (already
    processed or cross-tenant). Only the approval state changes — no other
    student field is touched. Auth accounts / public.users rows are preserved.
    """
    response = (
        client.table("students")
        .update({"approval_status": new_status})
        .eq("student_id", str(student_id))
        .eq("institution_id", str(institution_id))
        .eq("approval_status", "pending")
        .select(STUDENT_APPROVAL_COLUMNS)
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