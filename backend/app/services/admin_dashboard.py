"""Admin dashboard service (Phase Admin-3).

Aggregates useful counts across the admin-managed tables and recent
admin_audit_log activity. All reads use the service-role client, matching the
existing database access pattern.
"""

from uuid import UUID

from supabase import Client

from app.db.supabase import get_admin_client
from app.repositories.admin_audit import list_audit_entries


def _count(
    client: Client,
    table: str,
    institution_id: UUID | str | None = None,
    **filters: object,
) -> int:
    """Count rows in a table with optional institution scope and filters."""
    query = client.table(table).select("*", count="exact")
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    for column, value in filters.items():
        query = query.eq(column, value)
    response = query.execute()
    return response.count or 0


def get_dashboard_summary(
    institution_id: UUID | str | None = None,
    client: Client | None = None,
    recent_audit_limit: int = 10,
) -> dict:
    """Return dashboard counts plus the most recent audit-log entries.

    ``institution_id`` scopes the institution-owned tables (knowledge sources,
    FAQs, notices, students). Platform-wide tables (documents, results, test
    results, attendance) are counted globally because they carry no direct
    institution column.
    """
    db = client or get_admin_client()

    counts = {
        "knowledge_sources": _count(db, "knowledge_sources", institution_id),
        "documents": _count(db, "documents"),
        "faqs": _count(db, "faqs", institution_id, is_active=True),
        "notices": _count(db, "notices", institution_id, is_active=True),
        "students": _count(db, "students", institution_id),
        "student_results": _count(db, "student_results"),
        "test_results": _count(db, "test_results"),
        "attendance_records": _count(db, "student_attendance"),
    }

    recent_audit = list_audit_entries(db, limit=recent_audit_limit)

    return {"counts": counts, "recent_audit": recent_audit}
