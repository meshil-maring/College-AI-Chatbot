"""Tenant-authorized student directory query orchestration."""

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.db.supabase import get_admin_client
from app.repositories.students import student_directory as repository
from app.schemas.students.student_directory import (
    StudentDirectoryFilter,
    StudentDirectoryResponse,
)
from app.services.academics.authorization import scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error

_MISSING_SCHEMA_CODES = {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}


def _read_database(operation):
    try:
        return operation()
    except APIError as exc:
        if getattr(exc, "code", None) in _MISSING_SCHEMA_CODES:
            raise AppError(
                "The student directory is unavailable. Apply the student directory "
                "migration and refresh the database schema cache.",
                503,
                "STUDENT_DIRECTORY_SCHEMA_UNAVAILABLE",
            ) from exc
        raise translate_database_error(exc) from exc


def list_directory(
    actor: dict[str, Any],
    *,
    search: str | None,
    status: StudentDirectoryFilter | None,
    program_id: UUID | None,
    limit: int,
    offset: int,
) -> StudentDirectoryResponse:
    tenant, _ = scope(actor)
    tenant_id = UUID(str(tenant))
    client = get_admin_client()
    permissions = validated_scope_permissions(client, actor, tenant_id)
    if not permission_matches(permissions, "students.read"):
        raise AppError("You do not have permission to view students.", 403, "FORBIDDEN")
    if not 1 <= limit <= 100 or not 0 <= offset <= 1_000_000:
        raise AppError("The requested directory page is invalid.", 422, "INVALID_PAGE")

    response = _read_database(
        lambda: repository.read_directory(
            client,
            actor=str(actor["user_id"]),
            tenant=tenant_id,
            search=" ".join(search.split()) if search and search.strip() else None,
            status=status,
            program_id=program_id,
            limit=limit,
            offset=offset,
        )
    )
    return StudentDirectoryResponse.model_validate(response)
