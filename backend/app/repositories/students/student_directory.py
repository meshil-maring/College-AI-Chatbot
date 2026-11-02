"""Read-only RPC access for the institution-scoped student directory."""

from typing import Any
from uuid import UUID

from supabase import Client


def read_directory(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    search: str | None,
    status: str | None,
    program_id: UUID | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    response = client.rpc(
        "read_admin_student_directory",
        {
            "p_actor": actor,
            "p_tenant": str(tenant),
            "p_search": search,
            "p_status": status,
            "p_program_id": str(program_id) if program_id else None,
            "p_limit": limit,
            "p_offset": offset,
        },
    ).execute()
    data = response.data
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise RuntimeError("Student directory RPC returned no response data")
    return data


def update_profile(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    student: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = client.rpc(
        "update_admin_student_profile",
        {
            "p_actor": actor,
            "p_tenant": str(tenant),
            "p_student": str(student),
            "p_student_name": payload["student_name"],
            "p_register_number": payload["register_number"],
            "p_university_roll_number": payload.get("university_roll_number"),
            "p_section": str(payload["academic_section_id"])
            if payload.get("academic_section_id")
            else None,
        },
    ).execute()
    return _mutation_data(response.data)


def set_active(
    client: Client, *, actor: str, tenant: UUID, student: UUID, active: bool
) -> dict[str, Any]:
    response = client.rpc(
        "set_admin_student_active",
        {
            "p_actor": actor,
            "p_tenant": str(tenant),
            "p_student": str(student),
            "p_active": active,
        },
    ).execute()
    return _mutation_data(response.data)


def delete_profile(
    client: Client, *, actor: str, tenant: UUID, student: UUID
) -> dict[str, Any]:
    response = client.rpc(
        "delete_unused_admin_student",
        {
            "p_actor": actor,
            "p_tenant": str(tenant),
            "p_student": str(student),
        },
    ).execute()
    return _mutation_data(response.data)


def _mutation_data(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise RuntimeError("Student management RPC returned no response data")
    return data
