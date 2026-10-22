"""Authoritative faculty and legacy attendance, including ended participation."""
from typing import Any
from app.repositories.students import student_academic_experience as experience_repo
from app.schemas.students.student_academic_experience import (
    StudentAttendanceOverall, StudentSubjectAttendanceRow,
)
from app.services.faculty.faculty_attendance_reporting import statistics
from .scope import _own_rosters, _subject_labels, _matches_subject


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
