"""Section and batch capacity checks for transfer requests."""

from app.core.errors import AppError


def assert_section_capacity(client, section_id: str | None, tenant: str) -> None:
    if not section_id:
        return
    section = (
        client.table("academic_sections")
        .select("capacity, is_active")
        .eq("academic_section_id", section_id)
        .eq("institution_id", tenant)
        .maybe_single()
        .execute()
    )
    row = section.data[0] if isinstance(section.data, list) and section.data else None
    if not row or not row.get("is_active"):
        raise AppError("Target section is not available.", 422, "SECTION_UNAVAILABLE")
    capacity = row.get("capacity")
    if capacity is None:
        return
    enrolled = (
        client.table("student_semester_registrations")
        .select("semester_registration_id", count="exact")
        .eq("academic_section_id", section_id)
        .eq("institution_id", tenant)
        .in_("status", ["assigned", "registered"])
        .execute()
    )
    taken = int(getattr(enrolled, "count", 0) or 0)
    if taken >= capacity:
        raise AppError("The target section is full.", 409, "SECTION_FULL")

