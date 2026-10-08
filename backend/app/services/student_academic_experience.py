"""Student Academic Experience & Performance — read-only service layer.

Aggregates EXISTING authoritative academic data into the student-facing
experience. This module creates no attendance, test, result or assignment
storage; it is a consumer of:

* the Faculty Attendance system (``faculty_attendance_rosters`` /
  ``faculty_attendance_sessions`` / ``faculty_attendance_records`` plus the
  already-merged legacy ``student_attendance`` mirror), aggregated with the
  SAME ``statistics()`` helper and the SAME ``MONITORING_THRESHOLD`` the
  Faculty Attendance reporting surface uses;
* the Faculty Tests & Examination lifecycle (``faculty_tests`` status
  vocabulary — ``DRAFT``/``CANCELLED`` are never student-visible);
* the existing published result services (``student_results`` and
  ``test_results`` rows already filtered to publication by
  ``app.services.student_results``).

Security model (reuses locked primitives; nothing weakened):

    Authenticated JWT
        -> current_user (``get_current_user``: users.id + server-resolved
           institution_id tenant)
        -> ``student_context.get_student_context`` (students row resolved
           server-side; eligibility: approved + active + institution active)
        -> ``assert_student_context_tenant`` (defence-in-depth)
        -> repository reads keyed by the server-resolved ``student_id`` and
           the mandatory ``institution_id`` equality filter

The caller never supplies identity: these functions accept the
``current_user`` dict only. There is NO ``student_id`` / ``user_id`` /
``institution_id`` / register-number / roll-number parameter, so a
client-supplied identifier cannot override the authenticated student. The
optional ``subject`` filter is a course-code string applied AFTER the
server-side scope is fixed — it can only narrow the caller's own rows.

Every row returned by the repository is re-checked defensively against the
resolved ``student_id``/``institution_id`` before it can influence a figure
(IDOR/tenant belt-and-braces on top of the query filters).

Teacher/internal metadata (``remarks``, imports, actors, ``marks_state``,
``version``, assessment ``description``) is never selected and can never
appear in a response.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import student_academic_experience as experience_repo
from app.schemas.student_academic_experience import (
    StudentAcademicTimeline,
    StudentAttendanceOverall,
    StudentSubjectAttendance,
    StudentSubjectAttendanceRow,
    StudentSubjectPerformance,
    StudentSubjectPerformanceList,
    StudentTimelineEvent,
    StudentUpcomingAssessment,
    StudentUpcomingAssessments,
)
from app.services import student_context as student_context_service
from app.services import student_results as student_results_service
from app.services.faculty_attendance_reporting import (
    MONITORING_THRESHOLD,
    statistics,
)

# Student-visible assessment states for UPCOMING views. DRAFT (internal
# authoring) and CANCELLED (withdrawn) are excluded by design; COMPLETED is
# not "upcoming". This is the existing lifecycle vocabulary, not a new one.
UPCOMING_TEST_STATUSES: tuple[str, ...] = ("SCHEDULED", "ONGOING")

DEFAULT_UPCOMING_LIMIT = 20
MAX_UPCOMING_LIMIT = 50
DEFAULT_TIMELINE_LIMIT = 40
MAX_TIMELINE_LIMIT = 100
MAX_SUBJECT_FILTER_CHARS = 64

EVENT_UPCOMING = "assessment_upcoming"
EVENT_COMPLETED = "assessment_completed"
EVENT_RESULT_PUBLISHED = "result_published"


def _validate_limit(value: int, maximum: int, default: int) -> int:
    if value is None:  # pragma: no cover - FastAPI always supplies a value
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > maximum:
        raise AppError(
            "Invalid limit filter", status_code=422, code="INVALID_FILTER"
        )
    return value


def _validate_subject(subject: str | None) -> str | None:
    """The subject filter is a course-code narrowing key — never identity."""
    if subject is None:
        return None
    text = str(subject).strip()
    if not text:
        return None
    if len(text) > MAX_SUBJECT_FILTER_CHARS:
        raise AppError(
            "Invalid subject filter", status_code=422, code="INVALID_FILTER"
        )
    return text


def _scope(current_user: dict[str, Any], db: Any) -> tuple[dict[str, Any], str]:
    """Resolve the eligible student + tenant, or raise (fail closed)."""
    student_ctx = student_context_service.get_student_context(current_user)
    student_context_service.assert_student_context_tenant(current_user, student_ctx)
    institution_id = student_ctx.get("institution_id")
    if institution_id is None:
        # Fail closed: a student without a resolvable tenant must never
        # receive rows from any institution.
        raise AppError(
            "No institution is linked to this account",
            status_code=403,
            code="TENANT_MISMATCH",
        )
    if not student_ctx.get("student_id"):
        raise AppError(
            "No student profile is linked to this account",
            status_code=404,
            code="STUDENT_PROFILE_NOT_FOUND",
        )
    return student_ctx, str(institution_id)


def _own_rosters(db: Any, student_ctx: dict[str, Any], tenant: str) -> list[dict]:
    """The student's own rosters, re-checked against identity AND tenant."""
    student_id = str(student_ctx["student_id"])
    rows = experience_repo.list_linked_rosters(db, student_id, tenant)
    return [
        row
        for row in (rows or [])
        if str(row.get("linked_student_id") or "") == student_id
        and str(row.get("institution_id") or "") == tenant
        and row.get("section_id")
    ]


def _subject_labels(db: Any, rosters: list[dict]) -> dict[str, dict[str, Any]]:
    """section_id -> subject/section labels (no internal ids projected)."""
    section_ids = list({str(row["section_id"]) for row in rosters})
    sections = [
        row
        for row in experience_repo.list_sections(db, section_ids)
        if str(row.get("section_id") or "") in set(section_ids)
    ]
    offering_ids = list(
        {str(row["course_offering_id"]) for row in sections if row.get("course_offering_id")}
    )
    offerings = {
        str(row["course_offering_id"]): row
        for row in experience_repo.list_course_offerings(db, offering_ids)
    }
    course_ids = list(
        {str(row["course_id"]) for row in offerings.values() if row.get("course_id")}
    )
    courses = {
        str(row["course_id"]): row
        for row in experience_repo.list_courses(db, course_ids)
    }
    labels: dict[str, dict[str, Any]] = {}
    for section in sections:
        offering = offerings.get(str(section.get("course_offering_id") or ""), {})
        course = courses.get(str(offering.get("course_id") or ""), {})
        labels[str(section["section_id"])] = {
            "subject_code": _text(course.get("code")),
            "subject_name": _text(course.get("name")),
            "section_label": _text(section.get("code")) or _text(section.get("name")),
        }
    return labels


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _matches_subject(label: dict[str, Any], subject: str | None) -> bool:
    """Course-code narrowing (case-insensitive) applied AFTER scoping."""
    if subject is None:
        return True
    code = (label.get("subject_code") or "").strip().casefold()
    name = (label.get("subject_name") or "").strip().casefold()
    needle = subject.strip().casefold()
    return needle in {code, name}


def _merged_attendance_records(
    db: Any,
    rosters: list[dict],
    student_ctx: dict[str, Any],
    tenant: str,
) -> list[dict]:
    """Per-roster merged attendance, mirroring the Faculty reporting merge.

    Faculty records (session-based) are combined with the legacy mirrored
    ``student_attendance`` rows deduplicated by roster + date — exactly what
    ``faculty_attendance_reporting.section_data`` already does for the faculty
    surface, so both roles see identical numbers for the same student.
    """
    student_id = str(student_ctx["student_id"])
    roster_ids = {str(row["roster_id"]) for row in rosters}
    section_to_roster = {str(row["section_id"]): str(row["roster_id"]) for row in rosters}
    section_ids = list(section_to_roster)

    sessions = [
        row
        for row in experience_repo.list_section_sessions(db, tenant, section_ids)
        if str(row.get("institution_id") or "") == tenant
        and str(row.get("section_id") or "") in section_to_roster
    ]
    session_dates = {
        str(row["session_id"]): str(row["session_date"])
        for row in sessions
        if row.get("session_id") and row.get("session_date") is not None
    }

    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in experience_repo.list_records_for_rosters(db, list(roster_ids)):
        roster_id = str(row.get("roster_id") or "")
        session_date = session_dates.get(str(row.get("session_id") or ""))
        if roster_id not in roster_ids or session_date is None:
            # A record is only usable when both ends belong to the student's
            # own rosters inside the student's own sections.
            continue
        merged.append({"roster_id": roster_id, "session_date": session_date, "status": row.get("status")})
        seen.add((roster_id, session_date))

    for row in experience_repo.list_legacy_attendance(db, tenant, student_id, section_ids):
        if str(row.get("student_id") or "") != student_id:
            continue
        if str(row.get("institution_id") or "") != tenant:
            continue
        roster_id = section_to_roster.get(str(row.get("section_id") or ""))
        if roster_id is None or row.get("date") is None:
            continue
        session_date = str(row["date"])
        if (roster_id, session_date) in seen:
            continue
        merged.append({"roster_id": roster_id, "session_date": session_date, "status": row.get("status")})
        seen.add((roster_id, session_date))
    return merged


def _subject_attendance(
    db: Any,
    student_ctx: dict[str, Any],
    tenant: str,
    subject: str | None,
) -> tuple[list[StudentSubjectAttendanceRow], StudentAttendanceOverall]:
    rosters = _own_rosters(db, student_ctx, tenant)
    labels = _subject_labels(db, rosters)
    merged = _merged_attendance_records(db, rosters, student_ctx, tenant)

    by_roster: dict[str, list[dict]] = {}
    for record in merged:
        by_roster.setdefault(record["roster_id"], []).append(record)

    rows: list[StudentSubjectAttendanceRow] = []
    kept_records: list[dict] = []
    for roster in rosters:
        label = labels.get(str(roster["section_id"]), {})
        if not _matches_subject(label, subject):
            continue
        roster_records = by_roster.get(str(roster["roster_id"]), [])
        kept_records.extend(roster_records)
        stats = statistics(roster_records)
        rows.append(
            StudentSubjectAttendanceRow(
                subject_code=label.get("subject_code"),
                subject_name=label.get("subject_name"),
                section_label=label.get("section_label"),
                records_available=stats["record_count"] > 0,
                classes_conducted=stats["record_count"],
                classes_present=stats["present"],
                classes_absent=stats["absent"],
                classes_late=stats["late"],
                classes_excused=stats["excused"],
                attendance_percentage=stats["attendance_percentage"],
                below_threshold=(
                    stats["low_attendance"] if stats["record_count"] else None
                ),
            )
        )
    rows.sort(
        key=lambda row: (
            (row.subject_code or "~").casefold(),
            (row.section_label or "~").casefold(),
        )
    )

    overall_stats = statistics(kept_records)
    overall = StudentAttendanceOverall(
        records_available=overall_stats["record_count"] > 0,
        classes_conducted=overall_stats["record_count"],
        classes_present=overall_stats["present"],
        classes_absent=overall_stats["absent"],
        classes_late=overall_stats["late"],
        classes_excused=overall_stats["excused"],
        attendance_percentage=overall_stats["attendance_percentage"],
        below_threshold=(
            overall_stats["low_attendance"]
            if overall_stats["record_count"]
            else None
        ),
    )
    return rows, overall


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _upcoming_assessments(
    db: Any,
    student_ctx: dict[str, Any],
    tenant: str,
    subject: str | None,
    limit: int,
) -> list[StudentUpcomingAssessment]:
    """Student-visible upcoming assessments for the student's own sections.

    Visibility follows the existing ``faculty_tests`` lifecycle: only
    ``SCHEDULED`` (dated today or later) and ``ONGOING`` rows are surfaced.
    ``DRAFT`` (internal authoring) and ``CANCELLED`` (withdrawn) rows are
    never returned, and no description / marks-state / actor field is read.
    """
    rosters = _own_rosters(db, student_ctx, tenant)
    labels = _subject_labels(db, rosters)
    section_id_set = {str(row["section_id"]) for row in rosters}
    section_ids = sorted(section_id_set)
    if not section_ids:
        return []

    test_types = experience_repo.list_test_types(db)
    today = datetime.now(UTC).date()
    items: list[StudentUpcomingAssessment] = []
    for row in experience_repo.list_faculty_tests(
        db, tenant, section_ids, UPCOMING_TEST_STATUSES, limit=limit
    ):
        if str(row.get("institution_id") or "") != tenant:
            continue
        section_id = str(row.get("section_id") or "")
        if section_id not in section_id_set:
            continue
        status = str(row.get("status") or "")
        if status not in UPCOMING_TEST_STATUSES:
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        scheduled = _text(row.get("scheduled_date"))
        if status == "SCHEDULED":
            if scheduled is None:
                continue
            try:
                scheduled_date = date.fromisoformat(scheduled[:10])
            except ValueError:
                continue
            if scheduled_date < today:
                continue
        label = labels.get(section_id, {})
        if not _matches_subject(label, subject):
            continue
        type_code = _text(row.get("test_type"))
        items.append(
            StudentUpcomingAssessment(
                subject_code=label.get("subject_code"),
                subject_name=label.get("subject_name"),
                section_label=label.get("section_label"),
                title=title,
                test_type=type_code,
                test_type_name=_text(test_types.get(type_code)) if type_code else None,
                scheduled_date=scheduled,
                start_time=_text(row.get("start_time")),
                end_time=_text(row.get("end_time")),
                duration_minutes=_as_int(row.get("duration_minutes")),
                max_marks=_as_float(row.get("max_marks")),
                status=status,
            )
        )
    items.sort(
        key=lambda item: (item.scheduled_date or "9999-12-31", item.title.casefold())
    )
    return items[:limit]


def get_subject_attendance(
    current_user: dict[str, Any],
    subject: str | None = None,
    client: Any | None = None,
) -> StudentSubjectAttendance:
    """Return the authenticated student's own subject-wise attendance."""
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)
    subject_key = _validate_subject(subject)
    rows, overall = _subject_attendance(db, student_ctx, tenant, subject_key)
    return StudentSubjectAttendance(
        records_available=overall.records_available,
        monitoring_threshold=float(MONITORING_THRESHOLD),
        overall=overall,
        subjects=rows,
        subject_count=len(rows),
    )


def get_subject_attendance_dict(
    current_user: dict[str, Any],
    subject: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of :func:`get_subject_attendance` for the API layer."""
    return get_subject_attendance(
        current_user, subject=subject, client=client
    ).model_dump()


def get_upcoming_assessments(
    current_user: dict[str, Any],
    subject: str | None = None,
    limit: int = DEFAULT_UPCOMING_LIMIT,
    client: Any | None = None,
) -> StudentUpcomingAssessments:
    """Return the authenticated student's own upcoming assessments."""
    bounded = _validate_limit(limit, MAX_UPCOMING_LIMIT, DEFAULT_UPCOMING_LIMIT)
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)
    subject_key = _validate_subject(subject)
    items = _upcoming_assessments(db, student_ctx, tenant, subject_key, bounded)
    return StudentUpcomingAssessments(
        records_available=len(items) > 0, items=items, total=len(items)
    )


def _group_key(code: str | None, name: str | None) -> str:
    return ((code or name or "").strip()).casefold()


def _published_records(
    current_user: dict[str, Any],
    db: Any,
    subject: str | None,
) -> list[Any]:
    """Own PUBLISHED test scores, via the existing publication-filtered service.

    ``app.services.student_results.get_own_test_results`` already enforces
    ownership, tenant, ``status='published'`` and the
    ``faculty_tests.status in (PUBLISHED, LOCKED)`` rule — this layer never
    queries ``test_results`` directly and therefore cannot weaken it.
    """
    published = student_results_service.get_own_test_results(
        current_user, client=db, limit=100
    )
    return [
        record
        for record in published.records
        if _matches_subject(
            {
                "subject_code": record.course_code,
                "subject_name": record.course_name,
            },
            subject,
        )
    ]


def get_subject_performance(
    current_user: dict[str, Any],
    subject: str | None = None,
    client: Any | None = None,
) -> StudentSubjectPerformanceList:
    """Return subject-level attendance + published-score performance."""
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)
    subject_key = _validate_subject(subject)

    attendance_rows, _overall = _subject_attendance(
        db, student_ctx, tenant, subject_key
    )
    published_records = _published_records(current_user, db, subject_key)

    groups: dict[str, dict[str, Any]] = {}
    for row in attendance_rows:
        key = _group_key(row.subject_code, row.subject_name)
        groups[key] = {
            "subject_code": row.subject_code,
            "subject_name": row.subject_name,
            "section_label": row.section_label,
            "attendance_available": row.records_available,
            "attendance_percentage": row.attendance_percentage,
            "below_threshold": row.below_threshold,
            "records": [],
        }
    for record in published_records:
        key = _group_key(record.course_code, record.course_name)
        group = groups.setdefault(
            key,
            {
                "subject_code": record.course_code,
                "subject_name": record.course_name,
                "section_label": None,
                "attendance_available": False,
                "attendance_percentage": None,
                "below_threshold": None,
                "records": [],
            },
        )
        if not group["subject_name"] and record.course_name:
            group["subject_name"] = record.course_name
        group["records"].append(record)

    items: list[StudentSubjectPerformance] = []
    for group in groups.values():
        records = group["records"]
        percentages = [
            float(record.percentage)
            for record in records
            if record.percentage is not None
        ]
        scored = sorted(
            [
                record
                for record in records
                if record.percentage is not None and record.conducted_at
            ],
            key=lambda record: str(record.conducted_at),
        )
        latest = scored[-1] if scored else None
        items.append(
            StudentSubjectPerformance(
                subject_code=group["subject_code"],
                subject_name=group["subject_name"],
                section_label=group["section_label"],
                attendance_available=group["attendance_available"],
                attendance_percentage=group["attendance_percentage"],
                below_threshold=group["below_threshold"],
                assessments_completed=len(records),
                results_available=len(records) > 0,
                average_published_score=(
                    round(sum(percentages) / len(percentages), 2)
                    if percentages
                    else None
                ),
                latest_published_score=(
                    float(latest.percentage) if latest is not None else None
                ),
                latest_published_at=(
                    str(latest.conducted_at) if latest is not None else None
                ),
            )
        )
    items.sort(
        key=lambda item: (
            (item.subject_code or "~").casefold(),
            (item.section_label or "~").casefold(),
        )
    )
    return StudentSubjectPerformanceList(
        records_available=len(items) > 0, items=items, total=len(items)
    )


def get_academic_timeline(
    current_user: dict[str, Any],
    limit: int = DEFAULT_TIMELINE_LIMIT,
    client: Any | None = None,
) -> StudentAcademicTimeline:
    """Return a timeline DERIVED from existing authorized records only.

    Event sources (all deterministic, no fabrication):

    * ``assessment_upcoming``   — student-visible upcoming assessments
      (the same rows as ``GET /me/assessments/upcoming``);
    * ``assessment_completed``  — the student's own PUBLISHED test scores
      (conducted date), via the publication-filtered results service;
    * ``result_published``      — the student's own PUBLISHED academic
      results (issued date), via the publication-filtered results service.

    No timeline table exists or is created; every event carries only
    student-safe fields (no identifiers, no remarks, no audit metadata).
    """
    bounded = _validate_limit(limit, MAX_TIMELINE_LIMIT, DEFAULT_TIMELINE_LIMIT)
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)

    events: list[StudentTimelineEvent] = []

    for item in _upcoming_assessments(db, student_ctx, tenant, None, bounded):
        events.append(
            StudentTimelineEvent(
                date=item.scheduled_date,
                event_type=EVENT_UPCOMING,
                title=item.title,
                subject_code=item.subject_code,
                subject_name=item.subject_name,
                detail=item.test_type_name or item.status,
                score=None,
                max_marks=item.max_marks,
                percentage=None,
            )
        )

    for record in _published_records(current_user, db, None):
        title = _text(record.test_name) or "Assessment"
        events.append(
            StudentTimelineEvent(
                date=_text(record.conducted_at),
                event_type=EVENT_COMPLETED,
                title=title,
                subject_code=_text(record.course_code),
                subject_name=_text(record.course_name),
                detail=_text(record.outcome) or _text(record.mark_status),
                score=record.scored_marks,
                max_marks=record.max_marks,
                percentage=record.percentage,
            )
        )

    published_results = student_results_service.get_own_results(
        current_user, client=db
    )
    for record in published_results.records:
        result_type = _text(record.result_type)
        events.append(
            StudentTimelineEvent(
                date=_text(record.issued_at),
                event_type=EVENT_RESULT_PUBLISHED,
                title=result_type or "result",
                subject_code=None,
                subject_name=None,
                detail=_text(record.status),
                score=None,
                max_marks=None,
                percentage=None,
            )
        )

    events.sort(key=lambda event: (event.date or ""), reverse=True)
    bounded_events = events[:bounded]
    return StudentAcademicTimeline(
        records_available=len(bounded_events) > 0,
        items=bounded_events,
        total=len(bounded_events),
    )
