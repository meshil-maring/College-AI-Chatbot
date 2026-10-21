"""Phase 6.10 — Internal personalization context contracts.

These models are INTERNAL ONLY. They are never returned in the chat API
response and never persisted. They represent the controlled, minimal,
whitelisted view of an authenticated student's authorized data that is
rendered into the AI generation context.

Every value here is derived server-side from the authenticated JWT through
the Phase 6.9 access layer (``student_context`` / ``student_data``). No
client-supplied identity field ever reaches this object.

Explicitly EXCLUDED fields (must never appear here):
  - passwords, auth tokens, secrets
  - internal database ids the model does not need (student_id, user_id,
    institution_id, course_id, program_id, ...)
  - admin-only metadata (approval_status, is_active, created/updated audit)
  - any other student's information
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StudentIdentity(BaseModel):
    """Minimal, safe student identity shown to the model."""

    student_number: str | None = None
    program: str | None = None
    academic_year: str | None = None
    current_semester: str | None = None


class AttendanceRecord(BaseModel):
    """One attendance day (date + status only; no internal ids)."""

    date: str | None = None
    status: str | None = None


class AttendanceSummary(BaseModel):
    """Server-computed attendance summary. Percentage is authoritative."""

    records_available: bool = False
    total_classes: int = 0
    present_classes: int = 0
    absent_classes: int = 0
    late_classes: int = 0
    excused_classes: int = 0
    attendance_percentage: float | None = None
    recent_records: list[AttendanceRecord] = Field(default_factory=list)


class TestResultItem(BaseModel):
    """One published per-test score (values exactly as stored server-side)."""

    test_name: str | None = None
    test_type: str | None = None
    course: str | None = None
    max_marks: float | None = None
    scored_marks: float | None = None
    percentage: float | None = None
    letter_grade: str | None = None
    conducted_at: str | None = None


class AcademicResultItem(BaseModel):
    """One published consolidated academic result summary."""

    result_type: str | None = None
    total_credits_earned: float | None = None
    total_credits_max: float | None = None
    sgpa: float | None = None
    cgpa: float | None = None
    status: str | None = None
    issued_at: str | None = None


class CourseItem(BaseModel):
    """One course the student has authorized records for."""

    code: str | None = None
    name: str | None = None


class PersonalizationContext(BaseModel):
    """Controlled internal representation of authorized student data.

    ``intent`` records which deterministic intent triggered loading, so tests
    and diagnostics can verify data minimization (only required data loaded).
    """

    intent: str
    identity: StudentIdentity = Field(default_factory=StudentIdentity)
    attendance: AttendanceSummary | None = None
    test_results: list[TestResultItem] = Field(default_factory=list)
    academic_results: list[AcademicResultItem] = Field(default_factory=list)
    courses: list[CourseItem] = Field(default_factory=list)