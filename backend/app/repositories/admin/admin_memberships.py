"""Tenant-pinned data access for Phase 7.23 Staff/Faculty management."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError
from supabase import Client

from app.core.errors import AppError
from app.repositories.platform.tenancy import MEMBERSHIP_REQUEST_COLUMNS

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
    """Reject using the local atomic contract; never fall back to table writes."""
    if status != "rejected":
        raise ValueError("Membership rejection requires rejected status")
    try:
        response = client.rpc(
            "b05_reject_membership",
            {
                "p_request_id": str(request_id),
                "p_institution_id": str(institution_id),
                "p_decided_by": str(decided_by_user_id),
                "p_reason": reason,
            },
        ).execute()
    except APIError as exc:
        if exc.code not in {"PGRST202", "42883", "42703"}:
            raise
        raise AppError(
            "Membership rejection is unavailable. Contact your platform administrator.",
            503,
            "MEMBERSHIP_REJECTION_UNAVAILABLE",
        ) from None
    rows = _rows(response)
    return rows[0] if rows else None



def approve_and_grant_role(
    client: Client,
    *,
    request_id: UUID | str,
    institution_id: UUID | str,
    decided_by_user_id: UUID | str,
    reason: str | None,
) -> dict[str, Any]:
    response = client.rpc(
        "phase723_approve_membership_and_grant_role",
        {
            "p_request_id": str(request_id),
            "p_institution_id": str(institution_id),
            "p_decided_by": str(decided_by_user_id),
            "p_reason": reason,
        },
    ).execute()
    data = response.data if response is not None else None
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise RuntimeError("membership approval transaction returned no result")
    if "already_applied" in data and (
        "role_granted" not in data or "audit_persisted" not in data
    ):
        raise AppError(
            "Staff and faculty approval needs a database update. Contact your "
            "platform administrator, then retry sign-in setup for this request.",
            503,
            "MEMBERSHIP_APPROVAL_UNAVAILABLE",
        )
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
        .select(
            "id, auth_user_id, email, first_name, last_name, status, "
            "created_at, updated_at"
        )
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
