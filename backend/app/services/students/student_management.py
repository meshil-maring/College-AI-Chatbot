"""Permission-checked administrator mutations for institution student profiles."""

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.db.supabase import get_admin_client
from app.repositories.students import student_directory as repository
from app.schemas.students.student_directory import (
    StudentActiveResponse,
    StudentDeletionResponse,
)
from app.services.academics.authorization import scope, validated_scope_permissions

_MISSING_SCHEMA_CODES = {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}


def _context(actor: dict[str, Any], required: tuple[str, ...]):
    tenant, _ = scope(actor)
    tenant_id = UUID(str(tenant))
    client = get_admin_client()
    permissions = validated_scope_permissions(client, actor, tenant_id)
    if any(not permission_matches(permissions, code) for code in required):
        raise AppError("You do not have permission to manage this student.", 403, "FORBIDDEN")
    return client, tenant_id, str(actor["user_id"])


def _database(operation):
    try:
        return operation()
    except AppError:
        raise
    except APIError as exc:
        code = str(getattr(exc, "code", ""))
        if code in _MISSING_SCHEMA_CODES:
            raise AppError(
                "Student management is unavailable. Apply the student management migration.",
                503,
                "STUDENT_MANAGEMENT_SCHEMA_UNAVAILABLE",
            ) from exc
        errors = {
            "42501": (403, "FORBIDDEN", "You do not have permission to manage this student."),
            "P0002": (404, "STUDENT_NOT_FOUND", "Student record not found."),
            "23505": (409, "STUDENT_IDENTITY_EXISTS", "Register or university roll number is already in use."),
            "P1002": (409, "SECTION_CAPACITY", "The selected section is full."),
            "P1004": (409, "STUDENT_REGISTRATION_LOCKED", "A completed semester registration cannot be reassigned."),
            "P2003": (409, "STUDENT_HAS_LINKED_RECORDS", "This student has linked records and cannot be deleted. Deactivate the student to retain history."),
            "23514": (409, "STUDENT_STATE_CONFLICT", "The student cannot be changed in the requested way."),
            "22023": (422, "STUDENT_INPUT_INVALID", "Student details are invalid."),
        }
        status, public_code, message = errors.get(
            code, (500, "STUDENT_MANAGEMENT_FAILED", "Student management operation failed.")
        )
        raise AppError(message, status, public_code) from exc


def update_profile(actor: dict[str, Any], student: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    required = ("students.update",)
    if payload.get("academic_section_id") is not None:
        required += ("courses.manage",)
    client, tenant, actor_id = _context(actor, required)
    return _database(
        lambda: repository.update_profile(
            client,
            actor=actor_id,
            tenant=tenant,
            student=student,
            payload=payload,
        )
    )


def set_active(actor: dict[str, Any], student: UUID, active: bool) -> StudentActiveResponse:
    client, tenant, actor_id = _context(actor, ("students.update",))
    result = _database(
        lambda: repository.set_active(
            client, actor=actor_id, tenant=tenant, student=student, active=active
        )
    )
    return StudentActiveResponse.model_validate(result)


def delete_profile(actor: dict[str, Any], student: UUID) -> StudentDeletionResponse:
    client, tenant, actor_id = _context(actor, ("students.delete",))
    result = _database(
        lambda: repository.delete_profile(
            client, actor=actor_id, tenant=tenant, student=student
        )
    )
    return StudentDeletionResponse.model_validate(result)
