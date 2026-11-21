"""Tenant-scoped data access for academic placements used by transfers.

Placements are versioned historical records; a completed transfer creates a new
active placement while previous placements remain unchanged.
"""

from typing import Any
from uuid import UUID

from supabase import Client


def _row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        data = data[0] if data else None
    return data if isinstance(data, dict) else None


def resolve_current_placement(
    client: Client, *, student_id: UUID, tenant: UUID
) -> dict[str, Any] | None:
    """Resolve the student's live current placement from their latest semester registration."""
    response = (
        client.table("student_semester_registrations")
        .select(
            "academic_section_id, semester_id, status, assigned_at,"
            " academic_sections(admission_cohort_id, program_semester_id, name, code, capacity,"
            " admission_cohorts(program_id, curriculum_version_id, name, code,"
            " academic_batches!inner(batch_id, start_year, end_year, name, code)),"
            " program_semesters(program_id, semester_number, name, code),"
            " semesters(name, code))"
        )
        .eq("student_id", str(student_id))
        .eq("institution_id", str(tenant))
        .order("assigned_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return _row(response.data)


def get_active_placement(
    client: Client, *, student_id: UUID, tenant: UUID
) -> dict[str, Any] | None:
    response = (
        client.table("student_academic_placements")
        .select("*")
        .eq("student_id", str(student_id))
        .eq("institution_id", str(tenant))
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    return _row(response.data)


def list_placements(
    client: Client, *, student_id: UUID, tenant: UUID
) -> list[dict[str, Any]]:
    response = (
        client.table("student_academic_placements")
        .select("*")
        .eq("student_id", str(student_id))
        .eq("institution_id", str(tenant))
        .order("effective_from", desc=True)
        .execute()
    )
    return response.data if isinstance(response.data, list) else []


def create_placement(
    client: Client,
    *,
    actor: str,
    tenant: UUID,
    student_id: UUID,
    program_id: UUID,
    batch_id: UUID | None,
    section_id: UUID | None,
    semester_id: UUID | None,
    curriculum_version_id: UUID | None,
    effective_from: str,
) -> dict[str, Any]:
    response = (
        client.table("student_academic_placements")
        .insert(
            {
                "student_id": str(student_id),
                "institution_id": str(tenant),
                "program_id": str(program_id),
                "batch_id": str(batch_id) if batch_id else None,
                "section_id": str(section_id) if section_id else None,
                "semester_id": str(semester_id) if semester_id else None,
                "curriculum_version_id": (
                    str(curriculum_version_id) if curriculum_version_id else None
                ),
                "is_active": True,
                "effective_from": effective_from,
                "effective_to": None,
                "created_by": actor,
                "updated_by": actor,
            }
        )
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Academic placement insert returned no data")
    return row


def deactivate_placement(
    client: Client, *, placement_id: UUID, tenant: UUID
) -> dict[str, Any]:
    response = (
        client.table("student_academic_placements")
        .update({"is_active": False, "effective_to": None})
        .eq("placement_id", str(placement_id))
        .eq("institution_id", str(tenant))
        .eq("is_active", True)
        .execute()
    )
    row = _row(response.data)
    if not row:
        raise RuntimeError("Academic placement deactivation returned no data")
    return row
