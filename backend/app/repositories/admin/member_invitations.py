"""Tenant-pinned storage for Staff/Faculty invitations created by an administrator."""

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client

TABLE = "platform_admin_invitations"
COLUMNS = (
    "invitation_id, institution_id, email, role_name, status, expires_at, created_at, "
    "email_delivery_status, resend_count, last_sent_at, admin_invited, "
    "invited_department_id, invited_full_name"
)


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return [data] if isinstance(data, dict) else []


def create(
    client: Client,
    *,
    actor_id: UUID | str,
    institution_id: UUID | str,
    email: str,
    full_name: str,
    role: str,
    department_id: UUID | str,
    token_hash: str,
    expires_at: datetime,
    protected_token: str,
) -> dict[str, Any]:
    """Insert the invitation and its email job in one database transaction."""
    data = client.rpc("create_member_invitation", {
        "p_actor": str(actor_id),
        "p_tenant": str(institution_id),
        "p_email": email,
        "p_full_name": full_name,
        "p_role": role,
        "p_department": str(department_id),
        "p_token_hash": token_hash,
        "p_expires_at": expires_at.isoformat(),
        "p_protected_token": protected_token,
    }).execute().data
    if not isinstance(data, dict):
        raise RuntimeError("Invitation creation returned no row")
    return data


def list_staff_faculty(client: Client, institution_id: UUID | str) -> list[dict[str, Any]]:
    """Staff/Faculty invitations of one institution, newest first."""
    return _rows(
        client.table(TABLE)
        .select(COLUMNS)
        .eq("institution_id", str(institution_id))
        .in_("role_name", ["staff", "faculty"])
        .order("created_at", desc=True)
        .execute()
    )


def get(client: Client, institution_id: UUID | str, invitation_id: UUID | str) -> dict[str, Any] | None:
    """One Staff/Faculty invitation, only when it belongs to this institution."""
    rows = _rows(
        client.table(TABLE)
        .select(COLUMNS)
        .eq("invitation_id", str(invitation_id))
        .eq("institution_id", str(institution_id))
        .in_("role_name", ["staff", "faculty"])
        .limit(1)
        .execute()
    )
    return rows[0] if rows else None
