"""Tenant-pinned access to the department chosen for each Staff/Faculty member."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

TABLE = "institution_member_departments"


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return [data] if isinstance(data, dict) else []


def get_department(
    client: Client, institution_id: UUID | str, department_id: UUID | str
) -> dict[str, Any] | None:
    """Return the department only when it belongs to this institution."""
    rows = _rows(
        client.table("departments")
        .select("department_id, institution_id, code, name, is_active")
        .eq("department_id", str(department_id))
        .eq("institution_id", str(institution_id))
        .limit(1)
        .execute()
    )
    return rows[0] if rows else None


def list_assignments(client: Client, institution_id: UUID | str) -> list[dict[str, Any]]:
    """Every member department in the institution, with the department label."""
    return _rows(
        client.table(TABLE)
        .select("user_id, department_id, departments!inner(code, name)")
        .eq("institution_id", str(institution_id))
        .execute()
    )


def upsert_assignment(
    client: Client,
    *,
    institution_id: UUID | str,
    user_id: UUID | str,
    department_id: UUID | str,
    assigned_by: UUID | str,
) -> dict[str, Any] | None:
    rows = _rows(
        client.table(TABLE)
        .upsert(
            {
                "institution_id": str(institution_id),
                "user_id": str(user_id),
                "department_id": str(department_id),
                "assigned_by": str(assigned_by),
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="institution_id,user_id",
        )
        .execute()
    )
    return rows[0] if rows else None
