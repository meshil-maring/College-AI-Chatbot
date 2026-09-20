"""Phase 6.14.2 — Student-facing attendance data contracts.

Secure, reusable student-safe projection over the existing
``student_attendance`` rows (Phase Admin-1 table, Phase 6.7 hardening).

Derived server-side only via ``app.services.student_attendance`` — never from
client-supplied identifiers. Deliberately exposes NO internal database
identifiers (no ``student_attendance_id``, ``student_id``, ``user_id``,
``institution_id``, ``section_id``, ``program_id``, ``academic_year_id``,
``semester_id``).

Only fields already supported by the existing database are exposed:

* ``date`` / ``status`` / ``notes`` come straight from the stored row.
* Count/percentage fields are server-computed with the project's
  authoritative attendance rule (see
  ``app.services.personalization._build_attendance_summary``):
  ``total = len(rows)``; ``attendance_percentage =
  round(present / total * 100, 2)`` when ``total > 0`` else ``None``.
* No ``course`` / ``course_code`` / ``course_name`` / ``semester`` /
  ``academic_year`` label fields: the stored rows carry only
  ``section_id``/``academic_year_id``/``semester_id`` foreign keys and the
  project has no verified section->course label helper for the student
  self-service path, so label enrichment is out of scope (no invented fields).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StudentAttendanceRecord(BaseModel):
    """One student-safe attendance day (no internal database identifiers)."""

    date: str | None = None
    status: str | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentAttendanceSummary(BaseModel):
    """Server-computed attendance summary. Percentage is authoritative."""

    records_available: bool = False
    total_classes: int = 0
    present_classes: int = 0
    absent_classes: int = 0
    late_classes: int = 0
    excused_classes: int = 0
    attendance_percentage: float | None = None

    model_config = ConfigDict(extra="forbid")


class StudentOwnAttendance(BaseModel):
    """Combined student-facing attendance payload (summary + records)."""

    summary: StudentAttendanceSummary = Field(
        default_factory=StudentAttendanceSummary
    )
    records: list[StudentAttendanceRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
