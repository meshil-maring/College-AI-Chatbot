"""Bounded account, knowledge and communication summary for one institution.

The API supplies the institution resolved from the authenticated admin grant.
Every count is tenant filtered directly or through an institution-owned parent.
Recent notices are bounded; academic metrics and links have been retired.
"""

from uuid import UUID

from supabase import Client

from app.db.supabase import get_admin_client
from app.repositories.admin import admin_knowledge as knowledge_repo
from app.repositories.platform import tenancy as tenancy_repo
from app.schemas.admin.admin_dashboard import (
    DashboardCommunication,
    DashboardInstitution,
    DashboardKnowledge,
    DashboardQuickAction,
    DashboardRecentNotice,
    DashboardResponse,
    DashboardStudents,
)

# Bound on the "recent notices" list. The dashboard is a summary; the Notices
# management page remains the place for full, paginated records.
RECENT_NOTICES_LIMIT = 5

# Actions target the retained institution administration screens.
QUICK_ACTIONS: tuple[DashboardQuickAction, ...] = (
    DashboardQuickAction(
        view="approvals",
        label="Approve Student",
        description="Review the pending student approval queue.",
    ),
    DashboardQuickAction(
        view="documents",
        label="Upload Knowledge",
        description="Add documents to a knowledge source.",
    ),
    DashboardQuickAction(
        view="faqs",
        label="Manage FAQ",
        description="Create and publish frequently asked questions.",
    ),
    DashboardQuickAction(
        view="notices",
        label="Create Notice",
        description="Publish a notice for students to see.",
    ),
)


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


def _count_in(
    client: Client,
    table: str,
    institution_id: UUID | str,
    values: list[str],
) -> int:
    """Count institution-scoped rows whose column is any of ``values``.

    Same tenant guarantee as :func:`_count`: the institution filter is applied
    on the same query, never in Python, so a cross-tenant row can never be
    counted.
    """
    response = (
        client.table(table)
        .select("*", count="exact")
        .eq("institution_id", str(institution_id))
        .in_("lifecycle_status", values)
        .execute()
    )
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


def _institution_summary(
    client: Client,
    institution_id: UUID | str,
) -> DashboardInstitution:
    """Project the caller's own institution into safe display fields.

    Uses the same ``tenancy.get_institution_by_id`` read the Phase 7.20 guard
    used to verify lifecycle, so the dashboard cannot disagree with the guard
    about which institution it is describing. Only name/code/status are
    returned: no internal id, no contact details, no platform configuration.
    """
    row = tenancy_repo.get_institution_by_id(client, institution_id) or {}
    return DashboardInstitution(
        name=str(row.get("name") or "Unknown institution"),
        code=str(row.get("code") or ""),
        status=str(row.get("status") or "unknown"),
    )


def _students_summary(db: Client, institution_id: UUID | str) -> DashboardStudents:
    """Count students by the status vocabulary the app already uses."""
    return DashboardStudents(
        total=_count(db, "students", institution_id),
        pending_approvals=_count(
            db, "students", institution_id, approval_status="pending"
        ),
        approved=_count(db, "students", institution_id, approval_status="approved"),
        active=_count(db, "students", institution_id, status="active", is_active=True),
    )


def _knowledge_summary(db: Client, institution_id: UUID | str) -> DashboardKnowledge:
    """Count knowledge sources and documents for one institution.

    ``failed_processing_runs`` stays ``None``: resolving the tenant of a
    processing run requires a three-level nested embed that this phase does not
    add, and reporting ``0`` would be a fabricated metric.
    """
    return DashboardKnowledge(
        sources_total=_count(db, "knowledge_sources", institution_id),
        sources_active=_count_in(
            db,
            "knowledge_sources",
            institution_id,
            knowledge_repo.ACTIVE_LIFECYCLE_STATUSES,
        ),
        documents_total=_count_related(
            db, "documents", "document_id", "knowledge_sources", institution_id
        ),
        failed_processing_runs=None,
    )


def _communication_summary(
    db: Client,
    institution_id: UUID | str,
    recent_limit: int,
) -> DashboardCommunication:
    """Count active FAQs/notices and list a bounded set of recent notices."""
    recent = knowledge_repo.list_notices(
        db, institution_id=institution_id, limit=recent_limit
    )
    return DashboardCommunication(
        active_faqs=_count(db, "faqs", institution_id, is_active=True),
        active_notices=_count(db, "notices", institution_id, is_active=True),
        recent_notices=[
            DashboardRecentNotice(
                title=str(row.get("title") or ""),
                category=str(row.get("category") or "general"),
                priority=str(row.get("priority") or "normal"),
                published_at=row.get("published_at"),
            )
            for row in recent
        ],
    )


def get_dashboard_summary(
    institution_id: UUID | str,
    client: Client | None = None,
    recent_notices_limit: int = RECENT_NOTICES_LIMIT,
) -> DashboardResponse:
    """Build the University Admin operational dashboard for ONE institution.

    ``institution_id`` MUST be the value the authorization dependency resolved
    from the server-owned grant. The service does not verify that, does not
    need to, and must never be handed a request-supplied tenant.
    """
    db = client or get_admin_client()
    return DashboardResponse(
        institution=_institution_summary(db, institution_id),
        students=_students_summary(db, institution_id),
        knowledge=_knowledge_summary(db, institution_id),
        communication=_communication_summary(db, institution_id, recent_notices_limit),
        quick_actions=list(QUICK_ACTIONS),
    )
