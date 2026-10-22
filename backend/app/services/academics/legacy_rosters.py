"""Atomic legacy subject writes with authoritative scope, history and auditing."""

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.repositories.academics import academic_packages as repository
from app.services.academics.academic_packages import translate_error


def assign_subject(db, user: dict, section_id, registration_id, permission: str) -> dict:
    try:
        data = repository.assign_legacy_subject(
            db, str(user["user_id"]), str(user["institution_id"]),
            str(section_id), str(registration_id), permission,
        )
    except APIError as error:
        if error.code == "23505":
            raise AppError("Subject membership changed. Refresh and try again.", 409,
                           "ROSTER_DUPLICATE") from error
        raise translate_error(error) from error
    return _projection(data)


def delete_roster(db, user: dict, roster_id) -> dict:
    try:
        data = repository.delete_legacy_roster(
            db, str(user["user_id"]), str(user["institution_id"]), str(roster_id),
        )
    except APIError as error:
        if error.code in {"23503", "23514", "P0001"}:
            raise AppError("Roster history and package participation must be preserved.",
                           409, "ROSTER_HAS_HISTORY") from error
        raise translate_error(error) from error
    return _projection(data)


def _projection(data) -> dict:
    if not isinstance(data, dict):
        raise AppError("Invalid academic database projection", 500,
                       "DATABASE_PROJECTION_INVALID")
    return data
