"""Authorize teaching assignments for administrators and Heads of Department.

The route admits active admin and faculty grants and pins the institution. The
SQL functions decide atomically whether the caller is an administrator or a
current HOD, and which assignments they may see, make, approve or end.
"""

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.academics import teaching_assignments as repository
from app.services.academics.database_errors import translate_database_error


TEACHING_ERRORS = {
    "P0002": (404, "TEACHING_ASSIGNMENT_NOT_FOUND", "The teaching assignment was not found."),
    "P1501": (422, "TEACHING_OFFERING_UNAVAILABLE", "Choose an active subject offering of your institution."),
    "P1502": (422, "TEACHING_FACULTY_INVALID", "Choose an active faculty member of your institution."),
    "P1503": (
        403, "TEACHING_SCOPE",
        "You can manage teaching only for departments you head. Requests are decided by the "
        "receiving Head of Department, or by an administrator when that department has no other head.",
    ),
    "P1504": (409, "TEACHING_ALREADY_DECIDED", "This request was already decided or withdrawn. Refresh to see it."),
    "P1505": (422, "TEACHING_DATES_INVALID", "The planned end must be on or after today and the start date."),
    "P1506": (422, "TEACHING_REASON_REQUIRED", "Give a reason of up to 500 characters when rejecting."),
    "23505": (409, "TEACHING_ALREADY_ASSIGNED", "This teacher already has this subject. Refresh to see it."),
    "42501": (403, "FORBIDDEN", "Only administrators and Heads of Department manage teaching assignments."),
}


def _call(operation):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        mapped = TEACHING_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise translate_database_error(exc) from exc


def _actor(user):
    tenant = user.get("institution_id")
    if not tenant or not user.get("user_id"):
        raise AppError("You do not have permission to perform this action", 403, "FORBIDDEN")
    return get_admin_client(), str(user["user_id"]), str(tenant)


def overview(user):
    return _call(lambda: repository.overview(*_actor(user)))


def options(user):
    return _call(lambda: repository.options(*_actor(user)))


def request(user, payload):
    def write():
        starts, ends = payload.get("starts_on"), payload.get("planned_end_on")
        return repository.request(
            *_actor(user), str(payload["academic_offering_id"]), str(payload["faculty_user_id"]),
            starts.isoformat() if starts else None, ends.isoformat() if ends else None,
        )
    return _call(write)


def decide(user, assignment_id, action, note):
    return _call(lambda: repository.decide(*_actor(user), assignment_id, action == "approve", note))


def end(user, assignment_id):
    return _call(lambda: repository.end(*_actor(user), assignment_id))
