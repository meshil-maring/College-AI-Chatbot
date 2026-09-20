"""Phase 6.14.3 — Student-facing result data contracts.

Secure, reusable student-safe projection over the existing result tables
(``student_results`` consolidated summaries + ``student_result_items``
per-course rows + ``test_results`` per-test scores; Phase Admin-1 tables,
Phase 6.8 hardening).

Derived server-side only via ``app.services.student_results`` — never from
client-supplied identifiers. Deliberately exposes NO internal database
identifiers (no ``student_result_id``, ``test_result_id``,
``student_result_item_id``, ``student_id``, ``user_id``, ``institution_id``,
``program_id``, ``course_id``, ``section_id``, ``academic_year_id``,
``semester_id``).

Only fields already supported by the existing database are exposed:

* test record: ``test_name`` / ``test_type`` / ``max_marks`` /
  ``scored_marks`` / ``percentage`` / ``letter_grade`` / ``conducted_at``
  come straight from the stored row; ``course_code`` / ``course_name`` are
  benign reference labels resolved via the existing personalization label
  helper for the student's own authorized rows only (None when unresolvable).
* academic record: ``result_type`` / ``total_credits_earned`` /
  ``total_credits_max`` / ``sgpa`` / ``cgpa`` / ``status`` / ``issued_at``
  come straight from the stored row (status is always ``published`` for the
  student-facing path — the publication filter is enforced in the service).
* subject/course item: ``credits_earned`` / ``credits_max`` /
  ``grade_points`` / ``letter_grade`` / ``grade_value`` come straight from
  the stored row; ``course_code`` / ``course_name`` labels as above.

Publication rule (reused, not invented): only rows with
``status == "published"`` are ever projected. ``draft`` / ``withheld`` rows
stay admin-only (see ``app.services.admin_academics.RESULT_STATUSES`` /
``TEST_RESULT_STATUSES`` and ``app.services.student_data``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StudentTestResultRecord(BaseModel):
    """One student-safe published test/exam score (no internal ids)."""

    test_name: str | None = None
    test_type: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    max_marks: float | None = None
    scored_marks: float | None = None
    percentage: float | None = None
    letter_grade: str | None = None
    conducted_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentOwnTestResultsSummary(BaseModel):
    """Counts only — no invented aggregates (no average/percentage math)."""

    records_available: bool = False
    total_results: int = 0

    model_config = ConfigDict(extra="forbid")


class StudentOwnTestResults(BaseModel):
    """Combined student-facing test-result payload (summary + records)."""

    summary: StudentOwnTestResultsSummary = Field(
        default_factory=StudentOwnTestResultsSummary
    )
    records: list[StudentTestResultRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class StudentResultSubjectItem(BaseModel):
    """One student-safe per-course grade row (no internal ids)."""

    course_code: str | None = None
    course_name: str | None = None
    credits_earned: float | None = None
    credits_max: float | None = None
    grade_points: float | None = None
    letter_grade: str | None = None
    grade_value: float | None = None

    model_config = ConfigDict(extra="forbid")


class StudentAcademicResultRecord(BaseModel):
    """One student-safe published academic result summary (no internal ids)."""

    result_type: str | None = None
    total_credits_earned: float | None = None
    total_credits_max: float | None = None
    sgpa: float | None = None
    cgpa: float | None = None
    status: str | None = None
    issued_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentAcademicResultDetail(BaseModel):
    """One student-safe published academic result with subject rows."""

    result_type: str | None = None
    total_credits_earned: float | None = None
    total_credits_max: float | None = None
    sgpa: float | None = None
    cgpa: float | None = None
    status: str | None = None
    issued_at: str | None = None
    items: list[StudentResultSubjectItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class StudentOwnResultsSummary(BaseModel):
    """Counts only — no invented aggregates."""

    records_available: bool = False
    total_results: int = 0

    model_config = ConfigDict(extra="forbid")


class StudentOwnResults(BaseModel):
    """Combined student-facing academic-result payload (summary + records)."""

    summary: StudentOwnResultsSummary = Field(
        default_factory=StudentOwnResultsSummary
    )
    records: list[StudentAcademicResultRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
