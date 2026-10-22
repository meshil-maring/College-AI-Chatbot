"""Read-only student experience use cases.

Resolve authenticated ownership and tenant before reading records. Attendance
uses the faculty statistics helper; scores use the published-result service.
Ended package subjects retain attendance/results, while upcoming assessments
require current participation. Clients cannot override the student's identity.
"""
from typing import Any
from app.db.supabase import get_admin_client
from app.schemas.students.student_academic_experience import (
    StudentAcademicTimeline, StudentSubjectAttendance, StudentSubjectPerformanceList,
    StudentUpcomingAssessments,
)
from app.services.faculty.faculty_attendance_reporting import MONITORING_THRESHOLD
from app.services.students import student_results as student_results_service
from .academic_experience.scope import _scope, _validate_limit, _validate_subject
from .academic_experience.attendance import _subject_attendance
from .academic_experience.assessments import _upcoming_assessments
from .academic_experience.performance import _published_records, subject_performance
from .academic_experience.timeline import academic_timeline

DEFAULT_UPCOMING_LIMIT = 20
MAX_UPCOMING_LIMIT = 50
DEFAULT_TIMELINE_LIMIT = 40
MAX_TIMELINE_LIMIT = 100


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


def get_subject_performance(
    current_user: dict[str, Any], subject: str | None = None, client: Any | None = None,
) -> StudentSubjectPerformanceList:
    """Return historical attendance and published scores for the student."""
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)
    subject_key = _validate_subject(subject)
    attendance, _overall = _subject_attendance(db, student_ctx, tenant, subject_key)
    published = _published_records(current_user, db, subject_key)
    return subject_performance(attendance, published)


def get_academic_timeline(
    current_user: dict[str, Any], limit: int = DEFAULT_TIMELINE_LIMIT,
    client: Any | None = None,
) -> StudentAcademicTimeline:
    """Derive the student's timeline from authorized existing records."""
    bounded = _validate_limit(limit, MAX_TIMELINE_LIMIT, DEFAULT_TIMELINE_LIMIT)
    db = client or get_admin_client()
    student_ctx, tenant = _scope(current_user, db)
    upcoming = _upcoming_assessments(db, student_ctx, tenant, None, bounded)
    published = _published_records(current_user, db, None)
    results = student_results_service.get_own_results(current_user, client=db)
    return academic_timeline(upcoming, published, results, bounded)
