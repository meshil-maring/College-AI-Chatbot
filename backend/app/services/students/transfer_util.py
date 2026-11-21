"""Shared authorization and error-handling helpers for the transfer system."""

from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.security import authorize_permissions
from app.db.supabase import get_admin_client

_MISSING_SCHEMA_CODES = {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}


def _context(actor: dict[str, Any], required: tuple[str, ...]):
    """Resolve the tenant and authorize the actor's resolved permissions."""
    tenant = actor.get("institution_id")
    if not tenant:
        raise AppError("Institution scope is required.", 403, "SCOPE_MISSING")
    client = get_admin_client()
    authorize_permissions(actor, *required)
    return client, UUID(str(tenant)), str(actor["user_id"])


def _database(operation):
    try:
        return operation()
    except AppError:
        raise
    except Exception as exc:
        code = str(getattr(exc, "code", ""))
        if code in _MISSING_SCHEMA_CODES or code == "23505":
            raise AppError(
                "Transfer system is unavailable. Apply the student academic transfer migration.",
                503,
                "TRANSFER_SCHEMA_UNAVAILABLE",
            ) from exc
        if code == "42501":
            raise AppError("You do not have permission to perform this action.", 403, "FORBIDDEN") from exc
        raise AppError("Transfer operation failed.", 500, "TRANSFER_FAILED") from exc


def _audit(client, tenant, actor_id, action, table_name, record_id, record_data):
    client.table("admin_audit_log").insert({
        "actor_user_id": actor_id,
        "institution_id": str(tenant),
        "action": action,
        "table_name": table_name,
        "record_id": str(record_id),
        "record_data": record_data or {},
        "status": "success",
    }).execute()


def _actor_is_student(actor: dict[str, Any]) -> bool:
    return "student" in (actor.get("roles") or [])
