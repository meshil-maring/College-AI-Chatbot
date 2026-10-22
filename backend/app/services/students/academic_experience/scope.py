"""Resolve student ownership before applying presentation filters."""
from typing import Any
from app.core.errors import AppError
from app.repositories.students import student_academic_experience as experience_repo
from app.services.students import student_context as student_context_service

MAX_SUBJECT_FILTER_CHARS = 64


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
