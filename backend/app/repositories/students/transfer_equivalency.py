"""Tenant-scoped data access for subject equivalencies and transfer settings."""

from typing import Any
from uuid import UUID

from supabase import Client


def _row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        data = data[0] if data else None
    return data if isinstance(data, dict) else None


def list_equivalencies(
    client: Client,
    *,
    tenant: UUID,
    program_id: UUID | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    query = (
        client.table("subject_equivalencies")
        .select("*, subjects!subject_equivalencies_source_subject_id_fkey(name, code),"
        " subjects!subject_equivalencies_target_subject_id_fkey(name, code),"
        " programs(name, code)")
        .eq("institution_id", str(tenant))
    )
    if program_id is not None:
        query = query.eq("program_id", str(program_id))
    if active_only:
        query = query.eq("is_active", True)
    response = query.execute()
    return response.data if isinstance(response.data, list) else []


def create_equivalency(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = (
        client.table("subject_equivalencies")
        .insert({**payload, "institution_id": str(tenant), "created_by": actor})
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Subject equivalency insert returned no data")
    return row


def update_equivalency(
    client: Client,
    *,
    equivalency_id: UUID,
    tenant: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = (
        client.table("subject_equivalencies")
        .update(payload)
        .eq("equivalency_id", str(equivalency_id))
        .eq("institution_id", str(tenant))
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Subject equivalency update returned no data")
    return row


def get_transfer_settings(client: Client, *, tenant: UUID) -> dict[str, Any] | None:
    response = (
        client.table("institution_transfer_settings")
        .select("*")
        .eq("institution_id", str(tenant))
        .maybe_single()
        .execute()
    )
    return _row(response.data)


def upsert_transfer_settings(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = get_transfer_settings(client, tenant=tenant)
    if existing:
        response = (
            client.table("institution_transfer_settings")
            .update({**payload, "updated_by": actor})
            .eq("institution_id", str(tenant))
            .execute()
        )
    else:
        response = (
            client.table("institution_transfer_settings")
            .insert({**payload, "institution_id": str(tenant), "created_by": actor})
            .execute()
        )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Transfer settings upsert returned no data")
    return row
