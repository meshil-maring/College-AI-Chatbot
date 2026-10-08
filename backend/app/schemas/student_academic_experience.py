"""Student Academic Experience — student-facing data contracts.

Secure, read-only projection over EXISTING academic rows (Faculty Attendance
sessions/records, ``faculty_tests`` lifecycle, published ``test_results`` and
``student_results``). Nothing here introduces a new table, status or workflow.

Security/visibility rules encoded by these contracts:

* No internal database identifiers — no ``roster_id`` / ``session_id`` /
  ``record_id`` / ``test_id`` / ``test_result_id`` / ``student_id`` /
  ``institution_id`` / ``section_id`` fields exist in any model.
* No teacher-only fields — ``test_results.remarks``, import/actor metadata,
  ``marks_state``, ``version`` and assessment ``description`` are never part
  of these models.
* Publication state is enforced in the service layer BEFORE rows reach these
  models; a model can only ever be built from already-authorized rows.
* ``monitoring_threshold`` reuses the EXISTING Faculty Attendance monitoring
  threshold constant — no new policy value is introduced here.
* ``below_threshold`` is ``None`` (not ``False``) when no attendance records
  exist, so "no data" can never be rendered as "attendance is fine".
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StudentAttendanceOverall(BaseModel):
    """Authoritative aggregate over the student's recorded subject attendance."""

    records_available: bool = False
    classes_conducted: int = 0
    classes_present: int = 0
    classes_absent: int = 0
    classes_late: int = 0
    classes_excused: int = 0
    attendance_percentage: float | None = None
    below_threshold: bool | None = None

    model_config = ConfigDict(extra="forbid")


class StudentSubjectAttendanceRow(BaseModel):
    """One subject's attendance for the authenticated student."""

    subject_code: str | None = None
    subject_name: str | None = None
    section_label: str | None = None
    records_available: bool = False
    classes_conducted: int = 0
    classes_present: int = 0
    classes_absent: int = 0
    classes_late: int = 0
    classes_excused: int = 0
    attendance_percentage: float | None = None
    below_threshold: bool | None = None

    model_config = ConfigDict(extra="forbid")


class StudentSubjectAttendance(BaseModel):
    """Response of GET /students/me/attendance/subjects."""

    records_available: bool = False
    monitoring_threshold: float
    overall: StudentAttendanceOverall = Field(
        default_factory=StudentAttendanceOverall
    )
    subjects: list[StudentSubjectAttendanceRow] = Field(default_factory=list)
    subject_count: int = 0

    model_config = ConfigDict(extra="forbid")


class StudentUpcomingAssessment(BaseModel):
    """One student-visible upcoming assessment (never DRAFT/CANCELLED)."""

    subject_code: str | None = None
    subject_name: str | None = None
    section_label: str | None = None
    title: str
    test_type: str | None = None
    test_type_name: str | None = None
    scheduled_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: int | None = None
    max_marks: float | None = None
    status: str

    model_config = ConfigDict(extra="forbid")


class StudentUpcomingAssessments(BaseModel):
    """Response of GET /students/me/assessments/upcoming."""

    records_available: bool = False
    items: list[StudentUpcomingAssessment] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(extra="forbid")


class StudentSubjectPerformance(BaseModel):
    """One subject's performance row (published data only).

    ``average_published_score`` / ``latest_published_score`` are ``None``
    unless at least one PUBLISHED score exists for the subject — the service
    never averages drafts, unpublished marks or absent/no-score rows.
    """

    subject_code: str | None = None
    subject_name: str | None = None
    section_label: str | None = None
    attendance_available: bool = False
    attendance_percentage: float | None = None
    below_threshold: bool | None = None
    assessments_completed: int = 0
    results_available: bool = False
    average_published_score: float | None = None
    latest_published_score: float | None = None
    latest_published_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentSubjectPerformanceList(BaseModel):
    """Response of GET /students/me/performance/subjects."""

    records_available: bool = False
    items: list[StudentSubjectPerformance] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(extra="forbid")


class StudentTimelineEvent(BaseModel):
    """One derived timeline event (never an internal record identifier)."""

    date: str | None = None
    event_type: str
    title: str
    subject_code: str | None = None
    subject_name: str | None = None
    detail: str | None = None
    score: float | None = None
    max_marks: float | None = None
    percentage: float | None = None

    model_config = ConfigDict(extra="forbid")


class StudentAcademicTimeline(BaseModel):
    """Response of GET /students/me/timeline."""

    records_available: bool = False
    items: list[StudentTimelineEvent] = Field(default_factory=list)
    total: int = 0

    model_config = ConfigDict(extra="forbid")
