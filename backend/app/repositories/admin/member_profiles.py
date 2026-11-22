"""Tenant-pinned access to Staff/Faculty employee profiles and extra departments.

Reads filter by institution. Writes go through the audited database commands
(save_member_profile, set_member_additional_departments); the service role has
no direct write access to these tables.
"""

from typing import Any
from uuid import UUID

from supabase import Client

PROFILES = "institution_member_profiles"
FACULTY = "faculty_profiles"
STAFF = "staff_profiles"
ADDITIONAL = "institution_member_additional_departments"
COMMON_COLUMNS = "user_id, employee_id, phone, designation, joining_date"
FACULTY_COLUMNS = (
    "user_id, qualification, specialization, experience_years, employment_type, "
    "employment_start_date, contract_end_date"
)
STAFF_COLUMNS = (
    "user_id, staff_category, employment_type, employment_start_date, "
    "contract_end_date, responsibilities"
)


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return [data] if isinstance(data, dict) else []


def _select(
    client: Client, table: str, columns: str, institution_id: UUID | str, user_id: UUID | str | None
) -> list[dict[str, Any]]:
    query = client.table(table).select(columns).eq("institution_id", str(institution_id))
    if user_id is not None:
        query = query.eq("user_id", str(user_id))
    return _rows(query.execute())


def list_common(client: Client, institution_id: UUID | str, user_id: UUID | str | None = None):
    return _select(client, PROFILES, COMMON_COLUMNS, institution_id, user_id)


def list_faculty(client: Client, institution_id: UUID | str, user_id: UUID | str | None = None):
    return _select(client, FACULTY, FACULTY_COLUMNS, institution_id, user_id)


def list_staff(client: Client, institution_id: UUID | str, user_id: UUID | str | None = None):
    return _select(client, STAFF, STAFF_COLUMNS, institution_id, user_id)


def list_additional(client: Client, institution_id: UUID | str, user_id: UUID | str | None = None):
    """Additional departments with their labels, for one member or the institution."""
    return _select(
        client, ADDITIONAL, "user_id, department_id, departments!inner(code, name)",
        institution_id, user_id,
    )


def save_profile(
    client: Client, *, actor_id: UUID | str, institution_id: UUID | str,
    user_id: UUID | str, profile: dict[str, Any],
) -> dict[str, Any]:
    """Write the common and role profile and audit it in one transaction."""
    data = client.rpc("save_member_profile", {
        "p_actor": str(actor_id),
        "p_tenant": str(institution_id),
        "p_user": str(user_id),
        "p_profile": profile,
    }).execute().data
    if not isinstance(data, dict):
        raise RuntimeError("Profile save returned no result")
    return data


def set_additional_departments(
    client: Client, *, actor_id: UUID | str, institution_id: UUID | str,
    user_id: UUID | str, department_ids: list[UUID],
) -> dict[str, Any]:
    """Replace the member's additional departments and audit it in one transaction."""
    data = client.rpc("set_member_additional_departments", {
        "p_actor": str(actor_id),
        "p_tenant": str(institution_id),
        "p_user": str(user_id),
        "p_departments": [str(item) for item in department_ids],
    }).execute().data
    if not isinstance(data, dict):
        raise RuntimeError("Department update returned no result")
    return data
