"""Class In-Charge and Subject Coordinator appointments (User Management U6, U7).

Head of Department appointments stay with the transfer workflow that uses them
(``academics.student_transfers``). These two responsibilities are recorded and
shown now; the attendance and examination modules that would use them were
removed on 2026-10-23, so they grant no additional access yet.
"""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin import member_responsibilities as repo
from app.schemas.admin.member_responsibilities import (
    MemberResponsibilityAssign,
    MemberResponsibilityList,
    MemberResponsibilityResult,
    MemberResponsibilityView,
)

LABELS = {"class_in_charge": "Class In-Charge", "subject_coordinator": "Subject Coordinator"}
DATABASE_ERRORS = {
    "P1301": (422, "RESPONSIBILITY_TARGET_INVALID", "Choose an active class section or course of your institution."),
    "P1302": (422, "RESPONSIBILITY_FACULTY_INVALID", "Choose an active faculty member of your institution."),
    "22023": (
        422, "RESPONSIBILITY_TERM_INVALID",
        "The start date cannot be in the future and the planned end date cannot already have passed.",
    ),
    "P0002": (404, "RESPONSIBILITY_NOT_FOUND", "Responsibility not found."),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action."),
}


def _call(operation, failure: str):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        mapped = DATABASE_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise AppError(failure, 502, "RESPONSIBILITY_WRITE_FAILED") from exc


def list_responsibilities(actor: dict[str, Any], institution_id: UUID) -> MemberResponsibilityList:
    rows = _call(
        lambda: repo.list_responsibilities(
            get_admin_client(), actor_id=actor["user_id"], institution_id=institution_id),
        "Responsibilities could not be loaded. Try again.",
    )
    views = [MemberResponsibilityView.model_validate(row) for row in rows]
    return MemberResponsibilityList(responsibilities=views, total=len(views))


def assign(actor: dict[str, Any], institution_id: UUID, body: MemberResponsibilityAssign) -> MemberResponsibilityResult:
    row = _call(
        lambda: repo.assign(
            get_admin_client(), actor_id=actor["user_id"], institution_id=institution_id,
            faculty_user_id=body.faculty_user_id, responsibility=body.responsibility,
            target_id=body.target_id, starts_on=body.starts_on, planned_end_on=body.planned_end_on,
        ),
        "The responsibility could not be saved. Try again.",
    )
    label = LABELS[body.responsibility]
    already = bool(row.get("already_applied"))
    return MemberResponsibilityResult(
        responsibility_id=row["responsibility_id"],
        already_applied=already,
        message=f"Already the current {label}." if already else f"{label} assigned.",
    )


def end(actor: dict[str, Any], institution_id: UUID, responsibility_id: UUID) -> MemberResponsibilityResult:
    row = _call(
        lambda: repo.end(
            get_admin_client(), actor_id=actor["user_id"], institution_id=institution_id,
            responsibility_id=responsibility_id,
        ),
        "The responsibility could not be ended. Try again.",
    )
    label = LABELS.get(str(row.get("responsibility")), "Responsibility")
    already = bool(row.get("already_applied"))
    return MemberResponsibilityResult(
        responsibility_id=responsibility_id,
        already_applied=already,
        message=f"{label} had already ended." if already else f"{label} ended. It stays in the history.",
    )
