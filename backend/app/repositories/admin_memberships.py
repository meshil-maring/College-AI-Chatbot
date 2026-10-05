"""Tenant-pinned data access for Phase 7.23 Staff/Faculty management."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from app.repositories.tenancy import MEMBERSHIP_REQUEST_COLUMNS

ALLOWED_ROLES = frozenset({"staff", "faculty"})


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return [data] if isinstance(data, dict) else []


def list_requests(
    client: Client,
    institution_id: UUID | str,
    *,
    role: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        client.table("institution_membership_requests")
        .select(MEMBERSHIP_REQUEST_COLUMNS)
        .eq("institution_id", str(institution_id))
    )
    if role is not None:
        query = query.eq("requested_role", role)
    if status is not None:
        query = query.eq("status", status)
    return _rows(query.order("created_at", desc=True).execute())


def get_request_for_institution(
    client: Client, request_id: UUID | str, institution_id: UUID | str
) -> dict[str, Any] | None:
    response = (
        client.table("institution_membership_requests")
        .select(MEMBERSHIP_REQUEST_COLUMNS)
        .eq("request_id", str(request_id))
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def decide_pending_request(
    client: Client,
    *,
    request_id: UUID | str,
    institution_id: UUID | str,
    status: str,
    decided_by_user_id: UUID | str,
    reason: str | None,
) -> dict[str, Any] | None:
    """Atomic pending-only transition; concurrent losers receive no row."""
    response = (
        client.table("institution_membership_requests")
        .update(
            {
                "status": status,
                "decided_by_user_id": str(decided_by_user_id),
                "decided_at": datetime.now(timezone.utc).isoformat(),
                "decision_reason": reason,
            }
        )
        .eq("request_id", str(request_id))
        .eq("institution_id", str(institution_id))
        .eq("status", "pending")
        .execute()
    )
    rows = _rows(response)
    return rows[0] if rows else None


def approve_with_invitation(
    client: Client,
    *,
    request_id: UUID | str,
    institution_id: UUID | str,
    decided_by_user_id: UUID | str,
    reason: str | None,
    token_hash: str,
    expires_at: datetime,
    protected_token: str,
) -> dict[str, Any]:
    response = client.rpc(
        "phase723_approve_membership_with_invitation",
        {
            "p_request_id": str(request_id),
            "p_institution_id": str(institution_id),
            "p_decided_by": str(decided_by_user_id),
            "p_reason": reason,
            "p_token_hash": token_hash,
            "p_expires_at": expires_at.isoformat(),
            "p_protected_token": protected_token,
        },
    ).execute()
    data = response.data if response is not None else None
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise RuntimeError("membership approval transaction returned no result")
    return data


def list_scoped_role_grants(
    client: Client, institution_id: UUID | str
) -> list[dict[str, Any]]:
    response = (
        client.table("user_roles")
        .select(
            "user_id, assigned_at, roles!inner(name), "
            "users!inner(id, email, first_name, last_name, status, created_at, updated_at)"
        )
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .in_("roles.name", sorted(ALLOWED_ROLES))
        .execute()
    )
    return _rows(response)


def list_user_grants(client: Client, user_id: UUID | str) -> list[dict[str, Any]]:
    response = (
        client.table("user_roles")
        .select("scope_type, scope_id, roles!inner(name)")
        .eq("user_id", str(user_id))
        .execute()
    )
    return _rows(response)


def get_user(client: Client, user_id: UUID | str) -> dict[str, Any] | None:
    response = (
        client.table("users")
        .select("id, email, first_name, last_name, status, created_at, updated_at")
        .eq("id", str(user_id))
        .maybe_single()
        .execute()
    )
    return response.data if response is not None and response.data else None


def set_user_status(
    client: Client, user_id: UUID | str, *, expected: tuple[str, ...], status: str
) -> bool:
    response = (
        client.table("users")
        .update({"status": status})
        .eq("id", str(user_id))
        .in_("status", list(expected))
        .execute()
    )
    return bool(_rows(response))

