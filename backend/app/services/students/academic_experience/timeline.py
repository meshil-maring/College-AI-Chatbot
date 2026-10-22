"""Derive safe timeline events from authorized existing academic records."""
from app.schemas.students.student_academic_experience import (
    StudentAcademicTimeline, StudentTimelineEvent,
)
from .scope import _text

EVENT_UPCOMING = "assessment_upcoming"
EVENT_COMPLETED = "assessment_completed"
EVENT_RESULT_PUBLISHED = "result_published"


def academic_timeline(upcoming: list, published: list, published_results, bounded: int) -> StudentAcademicTimeline:
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
    events: list[StudentTimelineEvent] = []

    for item in upcoming:
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

    for record in published:
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
