"""Combine historical attendance and publication-filtered scores by subject."""
from typing import Any
from app.services.students import student_results as student_results_service
from app.schemas.students.student_academic_experience import (
    StudentSubjectPerformance, StudentSubjectPerformanceList,
)
from .scope import _matches_subject


def _group_key(code: str | None, name: str | None) -> str:
    return ((code or name or "").strip()).casefold()


def _published_records(
    current_user: dict[str, Any],
    db: Any,
    subject: str | None,
) -> list[Any]:
    """Own PUBLISHED test scores, via the existing publication-filtered service.

    ``app.services.students.student_results.get_own_test_results`` already enforces
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


def subject_performance(attendance_rows: list, published_records: list) -> StudentSubjectPerformanceList:
    """Aggregate already authorized attendance and published-score projections."""

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
