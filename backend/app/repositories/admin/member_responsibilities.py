"""Class In-Charge and Subject Coordinator appointments through audited commands.

The service role has no direct access to ``member_responsibilities``; every read
and write is a tenant-checked database function.
"""

from datetime import date
from typing import Any
from uuid import UUID

from supabase import Client


def list_responsibilities(client: Client, *, actor_id: UUID | str, institution_id: UUID | str) -> list[dict]:
    data = client.rpc("read_member_responsibilities", {
        "p_actor": str(actor_id), "p_tenant": str(institution_id),
    }).execute().data
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def assign(
    client: Client, *, actor_id: UUID | str, institution_id: UUID | str, faculty_user_id: UUID,
    responsibility: str, target_id: UUID, starts_on: date | None, planned_end_on: date | None,
) -> dict[str, Any]:
    data = client.rpc("assign_member_responsibility", {
        "p_actor": str(actor_id),
        "p_tenant": str(institution_id),
        "p_faculty": str(faculty_user_id),
        "p_responsibility": responsibility,
        "p_target": str(target_id),
        "p_starts_on": starts_on.isoformat() if starts_on else None,
        "p_planned_end_on": planned_end_on.isoformat() if planned_end_on else None,
    }).execute().data
    if not isinstance(data, dict):
        raise RuntimeError("Responsibility assignment returned no result")
    return data


def end(client: Client, *, actor_id: UUID | str, institution_id: UUID | str, responsibility_id: UUID) -> dict:
    data = client.rpc("end_member_responsibility", {
        "p_actor": str(actor_id),
        "p_tenant": str(institution_id),
        "p_responsibility_id": str(responsibility_id),
    }).execute().data
    if not isinstance(data, dict):
        raise RuntimeError("Ending the responsibility returned no result")
    return data
