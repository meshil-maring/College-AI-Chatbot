"""Phase 6.7 — Attendance service.

Business rules and tenant-safe orchestration over the existing
``student_attendance`` table (Phase Admin-1) hardened by the Phase 6.7
migration.

Authorization is enforced by the API layer (authentication, role, tenant,
ownership — locked Phase 6.6 RBAC). This service validates the academic
context and derives the tenant from the STUDENT record — never from the
client:

  * ``institution_id`` is server-derived from ``students.institution_id``.
  * the section must exist and belong to the student's institution;
  * attendance academic_year_id/semester_id must match the section's
    course offering (safely verifiable via the existing academic schema —
    there is no enrollment table, so per-section enrollment cannot be
    verified and that limitation is documented in PHASE_6_7_STATUS.md);
  * ownership fields can never be reassigned (schema + DB trigger).

The database trigger (``student_attendance_tenant_guard``) is the backstop
for every invariant enforced here, so concurrency/duplicate protection never
depends on application code alone.
"""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import attendance as attendance_repo
from app.services.admin_academics import (
    ATTENDANCE_STATUSES,
    AttendanceCreate,
    AttendanceUpdate,
    _validate_choice,
)

# Statuses mirror the student_attendance_status_check CHECK constraint
# (kept as the single source of truth in app.services.admin_academics).


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_attendance_status(status: str) -> None:
    """Reject any status outside the controlled vocabulary (422)."""
    return _validate_choice(status, ATTENDANCE_STATUSES, "attendance status")


def _duplicate_error(exc: Exception) -> AppError:
    """Map an insert failure to the most accurate business error.

    PostgREST surfaces the Postgres unique-violation SQLSTATE ``23505`` (or a
    ``duplicate key...`` message) for the (student_id, section_id, date)
    constraint. Everything else (foreign key violations, guard-trigger
    rejections) stays a generic 409 so no underlying schema detail leaks.
    """
    message = str(exc).lower()
    if "23505" in message or "duplicate" in message:
        return AppError(
            "Attendance record already exists for this student, section, and date",
            status_code=409,
            code="ATTENDANCE_DUPLICATE",
        )
    return AppError(
        "Attendance creation failed",
        status_code=409,
        code="ATTENDANCE_CREATE_FAILED",
    )


# ============================================================================
# Reads
# ============================================================================


def get_attendance(attendance_id: UUID | str) -> dict:
    """Return one attendance row, or raise 404 (tenant-guard helper entrypoint).

    The API layer uses the returned ``student_id`` for the caller-tenant
    assertion before any mutation.
    """
    db = get_admin_client()
    existing = attendance_repo.get_attendance_row(db, attendance_id)
    if existing is None:
        raise AppError(
            "Attendance record not found",
            status_code=404,
            code="ATTENDANCE_NOT_FOUND",
        )
    return existing
# ============================================================================
# Mutations
# ============================================================================


def create_attendance(payload: AttendanceCreate) -> dict:
    """Create one attendance record after server-side validation.

    Every input relationship is verified BEFORE the insert so the resulting
    error is precise: status vocabulary, student existence, section existence
    and its academic context, section<=>student tenant equality, and
    academic_year/semester consistency with the section's offering. The
    duplicate unique constraint is enforced by the database; races surface as
    ATTENDANCE_DUPLICATE (409).
    """
    _validate_attendance_status(payload.status)
    db = get_admin_client()

    student = attendance_repo.get_student_context(db, payload.student_id)
    if student is None:
        raise AppError("Student not found", status_code=404, code="STUDENT_NOT_FOUND")

    section = attendance_repo.get_section_academic_context(db, payload.section_id)
    if section is None or section.get("academic_year_id") is None:
        raise AppError("Section not found", status_code=404, code="SECTION_NOT_FOUND")

    # Tenant: an attendance row must belong to the student's institution, and
    # the section must belong to the same institution. A foreign section is
    # never silently accepted.
    if section.get("institution_id") != student.get("institution_id"):
        raise AppError(
            "The section does not belong to the student's institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    # Academic context: the row must describe the SAME offering as the section.
    if (
        section.get("academic_year_id") != str(payload.academic_year_id)
        or section.get("semester_id") != str(payload.semester_id)
    ):
        raise AppError(
            "Academic context (academic_year_id/semester_id) does not match the section",
            status_code=422,
            code="ACADEMIC_CONTEXT_MISMATCH",
        )

    row = payload.model_dump(mode="json")
    # The tenant is server-derived from the student record — never client input.
    row["institution_id"] = student["institution_id"]

    try:
        return attendance_repo.insert_attendance(db, row)
    except Exception as exc:
        raise _duplicate_error(exc) from exc


def update_attendance(
    attendance_id: UUID | str, payload: AttendanceUpdate
) -> dict:
    """Update only the permitted fields (status / notes).

    Ownership fields (student_id, section_id, academic_year_id, semester_id,
    institution_id) are not present in AttendanceUpdate — the schema rejects
    them, and the Phase 6.7 DB trigger refuses ownership reassignment even if
    a write bypasses this API.
    """
    db = get_admin_client()
    existing = attendance_repo.get_attendance_row(db, attendance_id)
    if existing is None:
        raise AppError(
            "Attendance record not found",
            status_code=404,
            code="ATTENDANCE_NOT_FOUND",
        )
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise AppError(
            "Attendance update payload is empty", status_code=422, code="EMPTY_UPDATE"
        )
    if "status" in fields:
        _validate_attendance_status(fields["status"])
    updated = attendance_repo.update_attendance_row(db, attendance_id, fields)
    return updated if updated is not None else existing


def delete_attendance(attendance_id: UUID | str) -> dict:
    """Hard-delete one attendance record (consistent with Phase Admin-1 policy;
    the project has no attendance soft-delete infrastructure).

    The caller must have passed tenant authorization with the returned
    student_id in mind — the API layer asserts it before calling here.
    """
    db = get_admin_client()
    existing = attendance_repo.get_attendance_row(db, attendance_id)
    if existing is None:
        raise AppError(
            "Attendance record not found",
            status_code=404,
            code="ATTENDANCE_NOT_FOUND",
        )
    attendance_repo.delete_attendance_row(db, attendance_id)
    return existing


def list_attendance_for_student(
    student_id: UUID | str,
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """List attendance rows for one student, most recent day first."""
    db = get_admin_client()
    return attendance_repo.list_attendance(
        db,
        student_id,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )