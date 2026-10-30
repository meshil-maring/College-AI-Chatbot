"""Authorize administrator setup and a student's own semester selection."""

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.core.security.scoped_permissions import permissions_for_scope
from app.db.supabase import get_admin_client
from app.repositories.academics import semester_registration as repository
from app.services.academics.authorization import scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error
from app.services.students import student_context


REGISTRATION_ERRORS = {
    "P1001": (422, "REGISTRATION_UNAVAILABLE", "The term has ended or a selected subject is not offered. Contact your administrator."),
    "P1002": (409, "REGISTRATION_CAPACITY", "The section or a selected subject has reached capacity. Refresh and try another option."),
    "P1003": (422, "REGISTRATION_SELECTION", "Choose exactly one complete option from every subject group."),
    "P1004": (409, "REGISTRATION_COMPLETE", "This registration is complete and cannot be changed here."),
}


def _call(operation):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        mapped = REGISTRATION_ERRORS.get(str(getattr(exc, "code", "")))
        if mapped:
            status, code, message = mapped
            raise AppError(message, status, code) from exc
        raise translate_database_error(exc) from exc


def _admin(user, *required):
    tenant, permissions = scope(user)
    _require(permissions, required)
    client = get_admin_client()
    permissions = validated_scope_permissions(client, user, tenant)
    _require(permissions, required)
    return client, tenant, permissions


def _require(permissions, required):
    if any(not permission_matches(permissions, item) for item in required):
        raise AppError("You do not have permission to perform this action", 403, "FORBIDDEN")


def catalogue(user):
    def read():
        client, tenant, permissions = _admin(user, "courses.read")
        can_read_students = permission_matches(permissions, "students.read")
        return {
            "institution_id": tenant,
            "groups": repository.choices(client, str(user["user_id"]), tenant),
            "students": repository.students(client, tenant) if can_read_students else [],
            "assignments": repository.assignments(client, tenant) if can_read_students else [],
            "can_manage_choices": permission_matches(permissions, "courses.manage"),
            "can_assign": can_read_students and all(permission_matches(permissions, item)
                for item in ("courses.manage", "students.update")),
        }
    return _call(read)


def save_group(user, payload, group_id=None, delete=False):
    def write():
        client, tenant, _ = _admin(user, "courses.manage")
        return repository.save_choices(client, str(user["user_id"]), tenant, payload, group_id, delete)
    return _call(write)


def assign_student(user, payload):
    def write():
        client, tenant, _ = _admin(user, "courses.manage", "students.read", "students.update")
        return repository.assign(client, str(user["user_id"]), tenant, payload)
    return _call(write)


def _student(user, action):
    context = student_context.get_student_context(user)
    student_context.assert_student_context_tenant(user, context)
    permissions = permissions_for_scope(user, "institution", context["institution_id"], allowed_roles={"student"})
    _require(permissions, [f"registration.own.{action}"])
    return get_admin_client(), str(context["institution_id"])


def own_semesters(user):
    def read():
        client, tenant = _student(user, "read")
        return repository.own_semesters(client, str(user["user_id"]), tenant)
    return _call(read)


def complete(user, registration_id, options):
    def write():
        client, tenant = _student(user, "manage")
        return repository.complete(client, str(user["user_id"]), tenant, registration_id, options)
    return _call(write)
