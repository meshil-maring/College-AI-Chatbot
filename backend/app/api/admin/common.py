"""Shared institution guards, database access and admin audit recording."""

from uuid import UUID

from app.core.errors import AppError
from app.core.security import assert_tenant_object, scope_tenant, user_tenant_id
from app.db.supabase import get_admin_client
from app.repositories.admin.admin_audit import record_admin_action
from app.schemas.admin.admin import AdminAuditLogCreate
from app.services.admin import admin_academics


def scope_institution(current_user: dict, requested: UUID | None) -> UUID:
    """Resolve the effective institution for an endpoint that accepts one."""
    institution_id = scope_tenant(current_user, requested)
    if institution_id is None:
        raise AppError("Institution scope required", 403, "SCOPE_MISSING")
    return institution_id


def required_institution(current_user: dict) -> UUID:
    institution_id = user_tenant_id(current_user)
    if institution_id is None:
        raise AppError("Institution scope required", 403, "SCOPE_MISSING")
    return institution_id


def assert_row_tenant(current_user: dict, institution_id: UUID | str | None) -> None:
    """Guard a fetched/created row against cross-tenant access."""
    # Global rows may be readable through public/student policy, but a
    # University Admin operation is always institution-owned. In particular,
    # this prevents a tenant admin from mutating global FAQ/notice rows.
    if institution_id is None:
        raise AppError(
            "This resource does not belong to your institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )
    assert_tenant_object(current_user, institution_id)


def assert_student_tenant(current_user: dict, student_id: UUID) -> None:
    """Guard any operation referencing a student: the student's institution
    must belong to the caller's tenant (no-op for platform admins)."""
    if user_tenant_id(current_user) is None:
        return
    student = admin_academics.get_student(student_id)
    if student is not None:
        assert_row_tenant(current_user, student.get("institution_id"))


def record_audit(
    current_user: dict,
    action: str,
    table_name: str | None,
    record_id: str | None = None,
    record_data: dict | None = None,
) -> None:
    """Persist one admin_audit_log entry for a privileged mutation."""
    record_admin_action(
        get_admin_client(),
        AdminAuditLogCreate(
            actor_user_id=UUID(current_user["user_id"]),
            institution_id=user_tenant_id(current_user),
            action=action,
            table_name=table_name,
            record_id=str(record_id) if record_id is not None else None,
            record_data=record_data,
        ),
    )
