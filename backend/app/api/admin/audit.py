"""Admin audit endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.errors import AppError
from app.core.security import user_tenant_id
from app.repositories.admin.admin_audit import get_audit_entry, list_audit_entries
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    actor_user_id: UUID | None = None,
    table_name: str | None = None,
    action: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    if (
        actor_user_id is not None
        and str(actor_user_id) != str(current_user["user_id"])
    ):
        raise AppError(
            "You do not have permission to view another user's audit records",
            status_code=403,
            code="FORBIDDEN",
        )
    db = common.get_admin_client()
    return list_audit_entries(
        db,
        limit=limit,
        actor_user_id=current_user["user_id"],
        institution_id=user_tenant_id(current_user),
        table_name=table_name,
        action=action,
        status=status,
    )


@router.get("/audit-logs/{audit_id}")
def get_audit_log(audit_id: UUID, current_user: dict = Depends(_ADMIN)) -> dict:
    db = common.get_admin_client()
    entry = get_audit_entry(db, audit_id)
    if entry is None:
        raise AppError("Audit entry not found", status_code=404, code="AUDIT_NOT_FOUND")
    institution_id = user_tenant_id(current_user)
    if institution_id is not None and str(entry.get("institution_id")) != str(institution_id):
        raise AppError(
            "You do not have permission to view this audit record",
            status_code=403,
            code="FORBIDDEN",
        )
    if str(entry.get("actor_user_id")) != str(current_user["user_id"]):
        raise AppError(
            "You do not have permission to view this audit record",
            status_code=403,
            code="FORBIDDEN",
        )
    return entry
