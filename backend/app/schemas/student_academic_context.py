"""Phase 6.14.4 — Student academic context contracts.

Single server-side aggregation model assembled ONLY by
``app.services.student_academic_context`` from the existing Phase 6.14.2
(attendance) and Phase 6.14.3 (results) services plus the Phase 6.14.1
academic-profile service.

Contract notes (verified against the existing codebase before writing):

* ``student`` reuses the Phase 6.14.1 field names (``register_number`` /
  ``university_roll_number`` / ``student_number``). ``name`` is present as a
  reserved ``None`` slot: the ``students`` table carries no verified name
  column and no existing self-service helper exposes a name, so inventing one
  (e.g. a new direct ``users``-table query) is out of scope for this phase.
* ``institution`` reuses the Phase 6.14.1 label names (``institution_name`` /
  ``institution_code``) — benign reference labels for the student's own
  tenant only.
* ``attendance`` reuses ``StudentOwnAttendance`` verbatim (summary + records,
  no internal ids) from Phase 6.14.2.
* ``results`` carries BOTH Phase 6.14.3 result families: consolidated
  academic results (``summary`` + ``records``) and per-test scores
  (``test_summary`` + ``test_records``). Only ``published`` rows are ever
  projected — the publication filter stays inside the existing results
  service; this model only transports what that service returns.

Safety: every model uses ``extra="forbid"``. No internal database identifiers
(``student_id`` / ``user_id`` / ``institution_id`` / ``program_id`` /
``academic_year_id`` / ``semester_id`` / ``section_id`` / ``course_id`` /
``*_result_id`` / ``student_attendance_id``), no passwords/auth secrets, and
no other student's data may enter this context. The resolver derives identity
exclusively from ``current_user`` (JWT ``user_id`` -> ``students.user_id``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.student_attendance import StudentOwnAttendance
from app.schemas.student_results import (
    StudentAcademicResultRecord,
    StudentOwnResultsSummary,
    StudentOwnTestResultsSummary,
    StudentTestResultRecord,
)


class StudentAcademicIdentity(BaseModel):
    """Student-safe identity block (no internal database identifiers).

    ``name`` is reserved and always ``None`` in this phase: there is no
    verified name column in the ``students`` contract consumed by the
    existing self-service layer, so no name is fabricated.
    """

    name: str | None = None
    student_number: str | None = None
    register_number: str | None = None
    university_roll_number: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentAcademicInstitution(BaseModel):
    """Benign institution labels for the student's own tenant."""

    institution_name: str | None = None
    institution_code: str | None = None

    model_config = ConfigDict(extra="forbid")


class StudentContextResults(BaseModel):
    """Both published result families (academic summaries + test scores)."""

    summary: StudentOwnResultsSummary = Field(
        default_factory=StudentOwnResultsSummary
    )
    records: list[StudentAcademicResultRecord] = Field(default_factory=list)
    test_summary: StudentOwnTestResultsSummary = Field(
        default_factory=StudentOwnTestResultsSummary
    )
    test_records: list[StudentTestResultRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class StudentAcademicContext(BaseModel):
    """Aggregated student-safe academic context for one authenticated student."""

    student: StudentAcademicIdentity = Field(
        default_factory=StudentAcademicIdentity
    )
    institution: StudentAcademicInstitution = Field(
        default_factory=StudentAcademicInstitution
    )
    attendance: StudentOwnAttendance = Field(
        default_factory=StudentOwnAttendance
    )
    results: StudentContextResults = Field(
        default_factory=StudentContextResults
    )

    model_config = ConfigDict(extra="forbid")
