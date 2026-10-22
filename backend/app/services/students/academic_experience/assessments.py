"""Upcoming assessments only for the student's current subject participation."""
from datetime import UTC, date, datetime
from typing import Any
from app.repositories.students import student_academic_experience as experience_repo
from app.schemas.students.student_academic_experience import StudentUpcomingAssessment
from .scope import _own_rosters, _subject_labels, _matches_subject, _text

UPCOMING_TEST_STATUSES = ("SCHEDULED", "ONGOING")


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
    # Ended package subjects retain history, but no future assessment obligation.
    rosters = [row for row in _own_rosters(db, student_ctx, tenant)
               if row.get("participation_active") is not False]
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
