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


def _count_related(
    client: Client,
    table: str,
    id_column: str,
    relationship: str,
    institution_id: UUID | str,
) -> int:
    """Count child rows through an inner join to an institution-owned parent."""
    response = (
        client.table(table)
        .select(
            f"{id_column}, {relationship}!inner(institution_id)",
            count="exact",
        )
        .eq(f"{relationship}.institution_id", str(institution_id))
        .execute()
    )
    return response.count or 0


def get_dashboard_summary(
    institution_id: UUID | str,
    actor_user_id: UUID | str,
    client: Client | None = None,
    recent_audit_limit: int = 10,
) -> dict:
    """Return dashboard counts plus the most recent audit-log entries.

    Every count is scoped to the authoritative institution. Tables without a
    direct institution column are filtered through their owning knowledge
    source or student relationship. The legacy audit table has no immutable
    institution column, so recent activity is conservatively restricted to the
    authenticated actor.
    """
    db = client or get_admin_client()

    counts = {
        "knowledge_sources": _count(db, "knowledge_sources", institution_id),
        "documents": _count_related(
            db,
            "documents",
            "document_id",
            "knowledge_sources",
            institution_id,
        ),
        "faqs": _count(db, "faqs", institution_id, is_active=True),
        "notices": _count(db, "notices", institution_id, is_active=True),
        "students": _count(db, "students", institution_id),
        "student_results": _count_related(
            db, "student_results", "student_result_id", "students", institution_id
        ),
        "test_results": _count_related(
            db, "test_results", "test_result_id", "students", institution_id
        ),
        "attendance_records": _count_related(
            db,
            "student_attendance",
            "student_attendance_id",
            "students",
            institution_id,
        ),
    }

    recent_audit = list_audit_entries(
        db,
        limit=recent_audit_limit,
        actor_user_id=actor_user_id,
    )

    return {"counts": counts, "recent_audit": recent_audit}
