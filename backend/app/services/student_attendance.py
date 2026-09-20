"""Phase 6.14.2 - Student attendance data integration service.

Secure, reusable student-facing attendance data layer. The authenticated
student retrieves ONLY their own attendance information.

Security model (reuses locked Phase 6 primitives; nothing weakened):

    Authenticated JWT -> current_user (get_current_user: users.user_id +
    server-resolved institution_id tenant) -> students row via users.user_id
    (server-side only) -> assert_tenant_object (cross-tenant rows fail
    closed with 403 TENANT_MISMATCH) -> own attendance rows via the
    existing attendance repository -> student-safe projection (whitelisted
    fields only, no internal database identifiers).

The caller never supplies identity: the service accepts the current_user
dict only. There is NO student_id / user_id / institution_id / email /
register-number / roll-number parameter, so client-supplied identifiers
cannot override the authenticated identity.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.security import assert_tenant_object
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo
from app.schemas.student_attendance import (
    StudentAttendanceRecord,
    StudentAttendanceSummary,
    StudentOwnAttendance,
)


def get_own_attendance(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    client: Any | None = None,
    limit: int = 200,
) -> StudentOwnAttendance:
    """Return the authenticated student's own attendance (summary+records)."""
    user_id = (current_user or {}).get("user_id")
    if not user_id:
        raise AppError(
            "Invalid authenticated user context",
            status_code=400,
            code="INVALID_USER_CONTEXT",
        )
    year_id = _validate_uuid_filter(academic_year_id, "academic_year_id")
    sem_id = _validate_uuid_filter(semester_id, "semester_id")
    start = _validate_date_filter(date_from, "date_from")
    end = _validate_date_filter(date_to, "date_to")
    if start is not None and end is not None and start > end:
        raise AppError(
            "Invalid date range: date_from must not be after date_to",
            status_code=422,
            code="INVALID_FILTER",
        )
    db = client or get_admin_client()
    student = academics_repo.get_student_by_user_id(db, str(user_id))
    if student is None:
        raise AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        )
    assert_tenant_object(current_user, student.get("institution_id"))
    rows = academics_repo.list_student_attendance(
        db,
        student["student_id"],
        academic_year_id=str(year_id) if year_id is not None else None,
        semester_id=str(sem_id) if sem_id is not None else None,
        date_from=start.isoformat() if start is not None else None,
        date_to=end.isoformat() if end is not None else None,
        limit=limit,
    )
    own_rows = [
        row
        for row in (rows or [])
        if str(row.get("student_id")) == str(student["student_id"])
    ]
    return StudentOwnAttendance(
        summary=_build_summary(own_rows),
        records=[_to_record(row) for row in own_rows],
    )


def get_own_attendance_dict(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    client: Any | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Dict form of get_own_attendance for the API layer."""
    return get_own_attendance(
        current_user,
        academic_year_id=academic_year_id,
        semester_id=semester_id,
        date_from=date_from,
        date_to=date_to,
        client=client,
        limit=limit,
    ).model_dump()


def _build_summary(rows: list[dict[str, Any]]) -> StudentAttendanceSummary:
    """Authoritative aggregation (mirrors personalization helper).

    attendance_percentage = round(present / total * 100, 2) when at
    least one record exists, else None. Zero records never divide.
    Unknown/blank statuses count toward the total but toward no
    bucket, exactly like _build_attendance_summary.
    """
    present = absent = late = excused = 0
    for row in rows:
        status = row.get("status")
        if not isinstance(status, str):
            status = str(status) if status is not None else ""
        status = status.strip().lower()
        if status == "present":
            present += 1
        elif status == "absent":
            absent += 1
        elif status == "late":
            late += 1
        elif status == "excused":
            excused += 1
    total = len(rows)
    percentage = round(present / total * 100, 2) if total else None
    return StudentAttendanceSummary(
        records_available=total > 0,
        total_classes=total,
        present_classes=present,
        absent_classes=absent,
        late_classes=late,
        excused_classes=excused,
        attendance_percentage=percentage,
    )


def _to_record(row: dict[str, Any]) -> StudentAttendanceRecord:
    """Project one stored row to the student-safe record (no ids)."""
    raw_date = row.get("date")
    text_date = str(raw_date).strip() if raw_date is not None else None
    raw_status = row.get("status")
    text_status = str(raw_status).strip() if raw_status is not None else None
    raw_notes = row.get("notes")
    text_notes = str(raw_notes).strip() if raw_notes is not None else None
    return StudentAttendanceRecord(
        date=text_date or None,
        status=text_status or None,
        notes=text_notes or None,
    )


def _validate_uuid_filter(value: UUID | str | None, name: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    text = str(value).strip()
    if not text:
        raise AppError(
            "Invalid " + name + " filter",
            status_code=422,
            code="INVALID_FILTER",
        )
    try:
        return UUID(text)
    except (ValueError, AttributeError, TypeError) as exc:
        raise AppError(
            "Invalid " + name + " filter",
            status_code=422,
            code="INVALID_FILTER",
        ) from exc


def _validate_date_filter(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except (ValueError, TypeError) as exc:
        raise AppError(
            "Invalid " + name + " filter (expected YYYY-MM-DD)",
            status_code=422,
            code="INVALID_FILTER",
        ) from exc

