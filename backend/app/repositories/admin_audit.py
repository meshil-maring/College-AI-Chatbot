"""Admin audit-trail repository.

Phase Admin-2 — Backend Contracts & Repositories.

All functions take an already-created Supabase ``Client`` as their first
argument (service-role client in production), following the existing
repository convention in ``app.repositories``.

Writes and reads target the ``admin_audit_log`` table created in Phase
Admin-1, which records privileged admin actions.
"""

from uuid import UUID

from supabase import Client

from app.schemas.admin import AdminAuditLogCreate

AUDIT_COLUMNS = (
    "audit_id, actor_user_id, action, table_name, record_id, record_data, "
    "ip_address, user_agent, status, performed_at"
)


def record_admin_action(client: Client, payload: AdminAuditLogCreate) -> dict:
    """Insert one audit-log entry and return the stored row."""
    row = payload.model_dump(mode="json")
    response = client.table("admin_audit_log").insert(row).execute()
    return response.data[0]


def get_audit_entry(client: Client, audit_id: UUID | str) -> dict | None:
    """Return one audit-log entry, or None when it does not exist."""
    response = (
        client.table("admin_audit_log")
        .select(AUDIT_COLUMNS)
        .eq("audit_id", str(audit_id))
        .maybe_single()
        .execute()
    )
    return response.data


def list_audit_entries(
    client: Client,
    limit: int = 50,
    actor_user_id: UUID | str | None = None,
    table_name: str | None = None,
    action: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List audit-log entries, most recent first, with optional filters."""
    query = client.table("admin_audit_log").select(AUDIT_COLUMNS)
    if actor_user_id is not None:
        query = query.eq("actor_user_id", str(actor_user_id))
    if table_name is not None:
        query = query.eq("table_name", table_name)
    if action is not None:
        query = query.eq("action", action)
    if status is not None:
        query = query.eq("status", status)
    response = query.order("performed_at", desc=True).limit(limit).execute()
    return response.data