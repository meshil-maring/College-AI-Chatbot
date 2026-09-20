"""Phase 6.14.3 - Student result data integration service."""

from __future__ import annotations

from numbers import Real
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.security import assert_tenant_object
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo
from app.repositories import personalization as personalization_repo
from app.schemas.student_results import (
    StudentAcademicResultDetail,
    StudentAcademicResultRecord,
    StudentOwnResults,
    StudentOwnResultsSummary,
    StudentOwnTestResults,
    StudentOwnTestResultsSummary,
    StudentResultSubjectItem,
    StudentTestResultRecord,
)
from app.services import student_data as student_data_service


def get_own_test_results(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Any | None = None,
    limit: int = 100,
) -> StudentOwnTestResults:
    """Return the authenticated student's own published test results."""
    user_id = (current_user or {}).get("user_id")
    if not user_id:
        raise AppError("Invalid authenticated user context",
            status_code=400, code="INVALID_USER_CONTEXT")
    year_id = _validate_uuid_filter(academic_year_id, "academic_year_id")
    sem_id = _validate_uuid_filter(semester_id, "semester_id")
    db = client or get_admin_client()
    student = academics_repo.get_student_by_user_id(db, str(user_id))
    if student is None:
        raise AppError("No student profile is linked to this account",
            status_code=404, code="STUDENT_PROFILE_NOT_FOUND")
    assert_tenant_object(current_user, student.get("institution_id"))
    rows = student_data_service.get_own_test_results(
        user_id,
        academic_year_id=str(year_id) if year_id is not None else None,
        semester_id=str(sem_id) if sem_id is not None else None,
        client=db, limit=limit)
    own_rows = [r for r in (rows or [])
        if str(r.get("student_id")) == str(student["student_id"])
        and r.get("status") == "published"]
    labels = _course_labels(db, own_rows)
    records = [_to_test_record(r, labels) for r in own_rows]
    summary = StudentOwnTestResultsSummary(
        records_available=len(records) > 0, total_results=len(records))
    return StudentOwnTestResults(summary=summary, records=records)


def get_own_test_results_dict(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Any | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Dict form of get_own_test_results for the API layer."""
    return get_own_test_results(current_user,
        academic_year_id=academic_year_id, semester_id=semester_id,
        client=client, limit=limit).model_dump()


def get_own_results(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Any | None = None,
) -> StudentOwnResults:
    """Return the authenticated student's own published academic results."""
    user_id = (current_user or {}).get("user_id")
    if not user_id:
        raise AppError("Invalid authenticated user context",
            status_code=400, code="INVALID_USER_CONTEXT")
    year_id = _validate_uuid_filter(academic_year_id, "academic_year_id")
    sem_id = _validate_uuid_filter(semester_id, "semester_id")
    db = client or get_admin_client()
    student = academics_repo.get_student_by_user_id(db, str(user_id))
    if student is None:
        raise AppError("No student profile is linked to this account",
            status_code=404, code="STUDENT_PROFILE_NOT_FOUND")
    assert_tenant_object(current_user, student.get("institution_id"))
    rows = student_data_service.get_own_results(
        user_id,
        academic_year_id=str(year_id) if year_id is not None else None,
        semester_id=str(sem_id) if sem_id is not None else None,
        client=db)
    own_rows = [r for r in (rows or [])
        if str(r.get("student_id")) == str(student["student_id"])
        and r.get("status") == "published"]
    records = [_to_academic_record(r) for r in own_rows]
    summary = StudentOwnResultsSummary(
        records_available=len(records) > 0, total_results=len(records))
    return StudentOwnResults(summary=summary, records=records)


def get_own_results_dict(
    current_user: dict[str, Any],
    academic_year_id: UUID | str | None = None,
    semester_id: UUID | str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of get_own_results for the API layer."""
    return get_own_results(current_user,
        academic_year_id=academic_year_id, semester_id=semester_id,
        client=client).model_dump()

def get_own_result(
    current_user: dict[str, Any],
    result_id: UUID | str,
    client: Any | None = None,
) -> StudentAcademicResultDetail:
    """Return ONE of the authenticated student's own published results."""
    user_id = (current_user or {}).get("user_id")
    if not user_id:
        raise AppError("Invalid authenticated user context",
            status_code=400, code="INVALID_USER_CONTEXT")
    db = client or get_admin_client()
    student = academics_repo.get_student_by_user_id(db, str(user_id))
    if student is None:
        raise AppError("No student profile is linked to this account",
            status_code=404, code="STUDENT_PROFILE_NOT_FOUND")
    assert_tenant_object(current_user, student.get("institution_id"))
    row = student_data_service.get_own_result(user_id, result_id, client=db)
    if (row is None
            or str(row.get("student_id")) != str(student["student_id"])
            or row.get("status") != "published"):
        raise AppError("Result not found",
            status_code=404, code="RESULT_NOT_FOUND")
    assert_tenant_object(current_user, row.get("institution_id"))
    detail = _to_academic_detail(row)
    labels = _course_labels(db, row.get("student_result_items") or [])
    if labels:
        for item, subject in zip(
                row.get("student_result_items") or [], detail.items):
            lbl = labels.get(str(item.get("course_id"))) \
                if item.get("course_id") is not None else None
            if lbl:
                subject.course_code = _as_str(lbl.get("code"))
                subject.course_name = _as_str(lbl.get("name"))
    return detail


def get_own_result_dict(
    current_user: dict[str, Any],
    result_id: UUID | str,
    client: Any | None = None,
) -> dict[str, Any]:
    """Dict form of get_own_result for the API layer."""
    return get_own_result(current_user, result_id, client=client).model_dump()


def _to_test_record(row: dict[str, Any],
        labels: dict[str, dict]) -> StudentTestResultRecord:
    lbl = labels.get(str(row.get("course_id"))) \
        if row.get("course_id") is not None else None
    return StudentTestResultRecord(
        test_name=_as_str(row.get("test_name")),
        test_type=_as_str(row.get("test_type")),
        course_code=_as_str((lbl or {}).get("code")),
        course_name=_as_str((lbl or {}).get("name")),
        max_marks=_as_float(row.get("max_marks")),
        scored_marks=_as_float(row.get("scored_marks")),
        percentage=_as_float(row.get("percentage")),
        letter_grade=_as_str(row.get("letter_grade")),
        conducted_at=_as_str(row.get("conducted_at")))


def _to_academic_record(row: dict[str, Any]) -> StudentAcademicResultRecord:
    return StudentAcademicResultRecord(
        result_type=_as_str(row.get("result_type")),
        total_credits_earned=_as_float(row.get("total_credits_earned")),
        total_credits_max=_as_float(row.get("total_credits_max")),
        sgpa=_as_float(row.get("sgpa")),
        cgpa=_as_float(row.get("cgpa")),
        status=_as_str(row.get("status")),
        issued_at=_as_str(row.get("issued_at")))


def _to_academic_detail(row: dict[str, Any]) -> StudentAcademicResultDetail:
    items = [StudentResultSubjectItem(
        course_code=None, course_name=None,
        credits_earned=_as_float(i.get("credits_earned")),
        credits_max=_as_float(i.get("credits_max")),
        grade_points=_as_float(i.get("grade_points")),
        letter_grade=_as_str(i.get("letter_grade")),
        grade_value=_as_float(i.get("grade_value")))
        for i in (row.get("student_result_items") or [])]
    return StudentAcademicResultDetail(
        result_type=_as_str(row.get("result_type")),
        total_credits_earned=_as_float(row.get("total_credits_earned")),
        total_credits_max=_as_float(row.get("total_credits_max")),
        sgpa=_as_float(row.get("sgpa")),
        cgpa=_as_float(row.get("cgpa")),
        status=_as_str(row.get("status")),
        issued_at=_as_str(row.get("issued_at")), items=items)


def _course_labels(db: Any, rows: list[dict[str, Any]]) -> dict[str, dict]:
    ids = {str(r.get("course_id")) for r in (rows or [])
           if r.get("course_id") is not None}
    if not ids:
        return {}
    try:
        return personalization_repo.get_course_labels(db, list(ids)) or {}
    except Exception:
        return {}


def _validate_uuid_filter(value: UUID | str | None, name: str) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    text = str(value).strip()
    if not text:
        raise AppError("Invalid " + name + " filter",
            status_code=422, code="INVALID_FILTER")
    try:
        return UUID(text)
    except (ValueError, AttributeError, TypeError) as exc:
        raise AppError("Invalid " + name + " filter",
            status_code=422, code="INVALID_FILTER") from exc


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

