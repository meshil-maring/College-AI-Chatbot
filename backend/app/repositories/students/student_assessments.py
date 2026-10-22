"""Tenant-scoped assessment metadata for student academic projections."""

from uuid import UUID
from supabase import Client
from app.repositories.shared.query_pages import read_all

TEST_COLUMNS = (
    "test_id, institution_id, section_id, title, test_type, max_marks, "
    "scheduled_date, start_time, end_time, duration_minutes, status"
)
TEST_TYPE_COLUMNS = "code, name"
MAX_TESTS = 100

def list_test_types(client: Client) -> dict[str, str]:
    """Small shared catalog: ``test_types`` code -> display name."""
    rows = read_all(
        client.table("test_types").select(TEST_TYPE_COLUMNS).order("code")
    )
    return {
        str(row.get("code")): str(row.get("name") or "")
        for row in rows
        if row.get("code")
    }


def list_faculty_tests(
    client: Client,
    institution_id: UUID | str,
    section_ids: list[UUID | str],
    statuses: tuple[str, ...],
    limit: int = 20,
) -> list[dict]:
    """Assessment metadata for the student's OWN sections.

    The caller passes the EXACT status vocabulary that is student-visible
    (never ``DRAFT`` / ``CANCELLED``); ordering is server-authoritative
    (earliest scheduled first). The projection never selects the assessment
    description, marks state, version or actor columns.
    """
    if not statuses:
        return []
    bounded = max(1, min(int(limit), MAX_TESTS))
    rows: list[dict] = []
    for start in range(0, len(section_ids), 100):
        batch = [str(value) for value in section_ids[start:start + 100]]
        rows.extend(
            read_all(
                client.table("faculty_tests")
                .select(TEST_COLUMNS)
                .eq("institution_id", str(institution_id))
                .in_("section_id", batch)
                .in_("status", list(statuses))
                .order("scheduled_date")
                .limit(bounded)
            )
        )
    rows.sort(
        key=lambda row: (
            str(row.get("scheduled_date") or "9999-12-31"),
            str(row.get("title") or ""),
        )
    )
    return rows[:bounded]

