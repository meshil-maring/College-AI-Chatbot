"""Tenant-pinned data access for switching a member between Staff and Faculty."""

from typing import Any
from uuid import UUID

from supabase import Client

MEMBER_ROLES = ("staff", "faculty")


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return [data] if isinstance(data, dict) else []


def role_ids(client: Client) -> dict[str, str]:
    """Role name to id for the two member roles."""
    rows = _rows(client.table("roles").select("id, name").in_("name", list(MEMBER_ROLES)).execute())
    return {str(row["name"]): str(row["id"]) for row in rows}


def member_grant(client: Client, institution_id: UUID | str, user_id: UUID | str) -> dict[str, Any] | None:
    """The member's Staff or Faculty grant in this institution, with its role name."""
    rows = _rows(
        client.table("user_roles")
        .select("user_id, role_id, roles!inner(name)")
        .eq("user_id", str(user_id))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .in_("roles.name", list(MEMBER_ROLES))
        .execute()
    )
    return rows[0] if rows else None


def has_direct_staff_grants(client: Client, institution_id: UUID | str, user_id: UUID | str) -> bool:
    rows = _rows(
        client.table("user_permission_grants")
        .select("grant_id")
        .eq("user_id", str(user_id))
        .eq("institution_id", str(institution_id))
        .limit(1)
        .execute()
    )
    return bool(rows)


def is_current_department_head(client: Client, institution_id: UUID | str, user_id: UUID | str) -> bool:
    rows = _rows(
        client.table("department_heads")
        .select("department_head_id")
        .eq("faculty_user_id", str(user_id))
        .eq("institution_id", str(institution_id))
        .is_("ended_at", "null")
        .limit(1)
        .execute()
    )
    return bool(rows)


def switch_role(
    client: Client,
    *,
    institution_id: UUID | str,
    user_id: UUID | str,
    from_role_id: str,
    to_role_id: str,
) -> list[dict[str, Any]]:
    """Move the grant from one member role to the other.

    Matching the current role id makes a concurrent change update nothing
    instead of overwriting it.
    """
    return _rows(
        client.table("user_roles")
        .update({"role_id": to_role_id})
        .eq("user_id", str(user_id))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
        .eq("role_id", from_role_id)
        .execute()
    )


def set_pending_request_role(
    client: Client, institution_id: UUID | str, request_id: UUID | str, role: str
) -> list[dict[str, Any]]:
    """Change the role a still-pending request will be approved as."""
    return _rows(
        client.table("institution_membership_requests")
        .update({"requested_role": role})
        .eq("request_id", str(request_id))
        .eq("institution_id", str(institution_id))
        .eq("status", "pending")
        .execute()
    )
