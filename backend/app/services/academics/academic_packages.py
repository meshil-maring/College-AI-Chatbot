"""Validated transport; package authority and atomicity remain in the database."""

import logging

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.core.security import resolve_primary_role, user_tenant_id
from app.db.supabase import get_admin_client
from app.repositories.academics import academic_packages as repository
from app.services.students.student_context import (
    assert_student_context_tenant,
    get_student_context,
)

logger = logging.getLogger(__name__)
MIGRATION = "20261021000000_academic_curriculum_packages.sql"
_MISSING = {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}


def translate_error(error: APIError) -> AppError:
    if error.code in _MISSING:
        logger.warning("event=academic_package_schema_missing database_code=%s", error.code)
        return AppError("Academic packages require a database update.", 503,
                        "ACADEMIC_PACKAGE_SCHEMA_UNAVAILABLE")
    if error.code == "23514" and error.message == "Package changes are closed for this class":
        return AppError("Package changes are closed for this class.", 409,
                        "ACADEMIC_PACKAGE_CLOSED")
    errors = {
        "42501": (403, "ACADEMIC_PACKAGE_FORBIDDEN", "This academic operation is not permitted in your scope."),
        "P0002": (404, "ACADEMIC_PACKAGE_NOT_FOUND", "The academic record is unavailable in your scope."),
        "23505": (409, "ACADEMIC_PACKAGE_CONFLICT", "The academic record already exists or has changed."),
        "23P01": (409, "ACADEMIC_PACKAGE_CONFLICT", "The academic assignment conflicts with another record."),
        "40001": (409, "ACADEMIC_PACKAGE_CONFLICT", "The assignment changed. Refresh and try again."),
        "P0001": (409, "ACADEMIC_PACKAGE_LOCKED", "The academic operation is closed or conflicts with its current state."),
        "23503": (422, "ACADEMIC_PACKAGE_INVALID", "An academic reference is unavailable."),
        "23514": (422, "ACADEMIC_PACKAGE_INVALID", "Check academic eligibility, package availability and subject mappings."),
        "22023": (422, "ACADEMIC_PACKAGE_INVALID", "The academic fields or relationships are invalid."),
        "22P02": (422, "ACADEMIC_PACKAGE_INVALID", "An academic identifier is invalid."),
    }
    status, code, message = errors.get(error.code, (
        500, "ACADEMIC_PACKAGE_FAILED", "The academic operation could not be completed.",
    ))
    return AppError(message, status, code)


def actor_scope(user: dict) -> tuple[str, str]:
    institution = user_tenant_id(user)
    if not institution or not user.get("user_id"):
        raise AppError("Institution scope required", 403, "SCOPE_MISSING")
    if resolve_primary_role(user.get("roles")) == "student":
        assert_student_context_tenant(user, get_student_context(user))
    return str(user["user_id"]), str(institution)


def _projection(data) -> dict:
    if not isinstance(data, dict):
        raise AppError("Invalid academic database projection", 500,
                       "DATABASE_PROJECTION_INVALID")
    return data


def catalogue(user: dict) -> dict:
    actor, institution = actor_scope(user)
    try:
        return _projection(repository.catalogue(get_admin_client(), actor, institution))
    except APIError as error:
        raise translate_error(error) from error


def command(user: dict, operation: str, payload: dict) -> dict:
    actor, institution = actor_scope(user)
    try:
        return _projection(repository.command(
            get_admin_client(), actor, institution, operation, payload,
        ))
    except APIError as error:
        raise translate_error(error) from error
