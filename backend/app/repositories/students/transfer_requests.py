"""Tenant-scoped data access for student academic transfer requests.

Mutations run through the service-role client; the service layer performs all
authorization and tenant checks before calling these functions.
"""

from typing import Any
from uuid import UUID

from supabase import Client

ACTIVE_REQUEST_STATUSES = ("submitted", "under_review", "eligible", "approved")


def _row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        data = data[0] if data else None
    return data if isinstance(data, dict) else None


def create_transfer_request(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = (
        client.table("transfer_requests")
        .insert(
            {
                **payload,
                "institution_id": str(tenant),
                "created_by": actor,
                "updated_by": actor,
            }
        )
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Transfer request insert returned no data")
    return row


def get_transfer_request(
    client: Client, *, request_id: UUID, tenant: UUID
) -> dict[str, Any] | None:
    response = (
        client.table("transfer_requests")
        .select("*")
        .eq("request_id", str(request_id))
        .eq("institution_id", str(tenant))
        .maybe_single()
        .execute()
    )
    return _row(response.data)


def list_transfer_requests(
    client: Client,
    *,
    tenant: UUID,
    student_id: UUID | None = None,
    status: str | None = None,
    transfer_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    query = (
        client.table("transfer_requests")
        .select("*", count="exact")
        .eq("institution_id", str(tenant))
    )
    if student_id is not None:
        query = query.eq("student_id", str(student_id))
    if status is not None:
        query = query.eq("status", status)
    if transfer_type is not None:
        query = query.eq("transfer_type", transfer_type)
    query = query.order("created_at", desc=True).limit(limit).offset(offset)
    response = query.execute()
    rows = response.data if isinstance(response.data, list) else []
    total = int(getattr(response, "count", 0) or 0)
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


def update_transfer_request(
    client: Client,
    *,
    request_id: UUID,
    tenant: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = (
        client.table("transfer_requests")
        .update(payload)
        .eq("request_id", str(request_id))
        .eq("institution_id", str(tenant))
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Transfer request update returned no data")
    return row


def record_transfer_action(
    client: Client,
    *,
    request_id: UUID,
    tenant: UUID,
    actor: str,
    action: str,
    comments: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
) -> dict[str, Any]:
    response = (
        client.table("transfer_request_actions")
        .insert(
            {
                "request_id": str(request_id),
                "institution_id": str(tenant),
                "actor_user_id": actor,
                "action": action,
                "comments": comments,
                "from_status": from_status,
                "to_status": to_status,
            }
        )
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Transfer action insert returned no data")
    return row


def get_recent_active_request(
    client: Client, *, student_id: UUID, tenant: UUID
) -> dict[str, Any] | None:
    response = (
        client.table("transfer_requests")
        .select("request_id, status, created_at, transfer_type")
        .eq("student_id", str(student_id))
        .eq("institution_id", str(tenant))
        .in_("status", list(ACTIVE_REQUEST_STATUSES))
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return _row(response.data)
