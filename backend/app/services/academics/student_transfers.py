"""Authorize student transfers, reviewer decisions and Head of Department appointments.

Python checks the caller's role scope early; the SQL functions repeat every
authorization step atomically. Students act only on their own placement, an
administrator reviews every request and a Head of Department reviews requests
into the department they currently head.
"""

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.core.security.scoped_permissions import permissions_for_scope
from app.db.supabase import get_admin_client
from app.repositories.academics import student_transfers as repository
from app.services.academics.authorization import scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error
from app.services.students import student_context


TRANSFER_ERRORS = {
    "P0002": (404, "TRANSFER_NOT_FOUND", "The transfer request or department was not found."),
    "P1101": (409, "TRANSFER_CLOSED", "This transfer request is already closed. Refresh to see its status."),
    "P1102": (
        409, "TRANSFER_PLACEMENT_CHANGED",
        "The student's section changed after this request was submitted. "
        "Reject it and ask the student to submit a new request.",
    ),
    "P1103": (422, "TRANSFER_TERM_CLOSED", "Transfers are available only while the current term is open."),
    "P1104": (422, "TRANSFER_TARGET_UNAVAILABLE", "The requested section is no longer available for this transfer."),
    "P1105": (409, "TRANSFER_SECTION_FULL", "The requested section has no free seats."),
    "P1106": (409, "TRANSFER_ALREADY_OPEN", "You already have an open transfer request."),
    "P1107": (
        422, "TRANSFER_NO_PLACEMENT",
        "You are not assigned to a section yet, so a transfer cannot be requested.",
    ),
    "P1108": (422, "TRANSFER_REASON_INVALID", "Explain the transfer in 10 to 2000 characters."),
    "P1109": (422, "TRANSFER_REASON_REQUIRED", "Enter a reason before rejecting this request."),
    "P1110": (
        422, "DEPARTMENT_HEAD_INVALID",
        "Choose an active faculty member of this institution for an active department.",
    ),
    "P1111": (
        409, "STUDENT_HAS_OPEN_TRANSFER",
        "This student has an open transfer request. Approve or reject it under Transfer Requests first.",
    ),
    "P1112": (422, "STUDENT_NO_PLACEMENT", "This student is not assigned to a section in an open term."),
    "P1113": (
        422, "TRANSFER_SEMESTER_MISMATCH",
        "Transfers must keep the same semester number. Only an administrator can override this.",
    ),
    "23505": (409, "TRANSFER_ALREADY_OPEN", "You already have an open transfer request."),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action."),
}


def _call(operation):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        mapped = TRANSFER_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise translate_database_error(exc) from exc


def _forbidden():
    return AppError("You do not have permission to perform this action", 403, "FORBIDDEN")


def _student(user, permission):
    context = student_context.get_student_context(user)
    student_context.assert_student_context_tenant(user, context)
    permissions = permissions_for_scope(
        user, "institution", context["institution_id"], allowed_roles={"student"}
    )
    if not permission_matches(permissions, permission):
        raise _forbidden()
    return get_admin_client(), str(context["institution_id"])


def _reviewer(user):
    # The route pins institution_id from an active admin/faculty grant. Whether
    # the caller is an administrator or a current HOD is decided in SQL.
    tenant = user.get("institution_id")
    if not tenant or not user.get("user_id"):
        raise _forbidden()
    return get_admin_client(), str(tenant)


def _department_admin(user, permission):
    tenant, permissions = scope(user)
    if not permission_matches(permissions, permission):
        raise _forbidden()
    client = get_admin_client()
    if not permission_matches(validated_scope_permissions(client, user, tenant), permission):
        raise _forbidden()
    return client, tenant


def own_transfers(user):
    def read():
        client, tenant = _student(user, "transfers.read")
        return repository.own_transfers(client, str(user["user_id"]), tenant)
    return _call(read)


def submit(user, payload):
    def write():
        client, tenant = _student(user, "transfers.request")
        return repository.submit(
            client, str(user["user_id"]), tenant, payload["to_section_id"], payload["reason"]
        )
    return _call(write)


def cancel(user, request_id):
    def write():
        client, tenant = _student(user, "transfers.request")
        return repository.cancel(client, str(user["user_id"]), tenant, request_id)
    return _call(write)


def reviews(user, open_only):
    def read():
        client, tenant = _reviewer(user)
        return repository.reviews(client, str(user["user_id"]), tenant, open_only)
    return _call(read)


def decide(user, request_id, payload):
    def write():
        comment = (payload.get("comment") or "").strip() or None
        if payload["action"] == "reject" and comment is None:
            raise AppError("Enter a reason before rejecting this request.", 422, "TRANSFER_REASON_REQUIRED")
        client, tenant = _reviewer(user)
        return repository.decide(
            client, str(user["user_id"]), tenant, request_id, payload["action"], comment
        )
    return _call(write)


def direct_students(user):
    def read():
        client, tenant = _reviewer(user)
        return repository.direct_students(client, str(user["user_id"]), tenant)
    return _call(read)


def direct_options(user, student_id):
    def read():
        client, tenant = _reviewer(user)
        return repository.direct_options(client, str(user["user_id"]), tenant, student_id)
    return _call(read)


def direct_transfer(user, payload):
    def write():
        client, tenant = _reviewer(user)
        return repository.direct_transfer(
            client, str(user["user_id"]), tenant,
            payload["student_id"], payload["to_section_id"], payload["reason"],
            bool(payload.get("allow_other_semester")),
        )
    return _call(write)


def department_heads(user):
    def read():
        client, tenant = _department_admin(user, "departments.read")
        return repository.department_heads(client, str(user["user_id"]), tenant)
    return _call(read)


def assign_department_head(user, department_id, faculty_user_id):
    def write():
        client, tenant = _department_admin(user, "departments.manage")
        return repository.assign_department_head(
            client, str(user["user_id"]), tenant, department_id, faculty_user_id
        )
    return _call(write)
