"""Phase 7.21 — University Admin operational dashboard service.

Reads a bounded, institution-scoped operational summary for exactly ONE
institution and projects it into the explicit ``DashboardResponse`` contract.

Reuse (nothing here is a new data-access pattern):

* ``_count`` / ``_count_related`` are the Phase 7.20 tenant-safe counting
  primitives already proven by ``tests/test_admin_dashboard_service.py``. Every
  count is either filtered by ``institution_id`` directly or resolved through
  an ``!inner`` join to an institution-owned parent.
* ``admin_knowledge.ACTIVE_LIFECYCLE_STATUSES`` and
  ``admin_knowledge.list_notices`` are the existing knowledge/notice
  projections, so "active source" and "recent notice" mean exactly what they
  mean on the management screens.
* ``tenancy.get_institution_by_id`` is the existing institution read used by the
  Phase 7.20 authorization guard, so the dashboard reads the same row the
  guard validated.

Authorization: this service NEVER accepts a tenant from the request. The
caller passes the institution that ``require_institution_roles`` already
resolved from the server-owned ``user_roles`` grant. There is deliberately no
``institution_id`` query parameter on the endpoint any more — a client-supplied
tenant can neither widen nor redirect the scope because it is never read.

Query shape: a fixed number of aggregate queries proportional to the number of
metrics (not to the number of rows), so there is no N+1 behaviour and no
unbounded list is ever materialised. ``recent_notices`` is explicitly bounded.

No cache, no background job, no materialized view, no analytics warehouse.
"""

from uuid import UUID

from supabase import Client

from app.db.supabase import get_admin_client
from app.repositories import admin_knowledge as knowledge_repo
from app.repositories import tenancy as tenancy_repo
from app.schemas.admin_dashboard import (
    DashboardAcademics,
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

# Phase 7.21 — every quick action below points at an admin screen that already
# exists (AdminShell navigation + its verified backend endpoints). No new
# feature module is introduced by the dashboard.
QUICK_ACTIONS: tuple[DashboardQuickAction, ...] = (
    DashboardQuickAction(
        view="approvals",
        label="Approve Student",
        description="Review the pending student approval queue.",
    ),
    DashboardQuickAction(
        view="students",
        label="Manage Students",
        description="View and update this institution's students.",
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
    DashboardQuickAction(
        view="attendance",
        label="Manage Attendance",
        description="Record and correct attendance.",
    ),
    DashboardQuickAction(
        view="results",
        label="Manage Results",
        description="Maintain result records for this institution.",
    ),
    DashboardQuickAction(
        view="test-results",
        label="Manage Tests",
        description="Maintain test result records for this institution.",
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
            db, "knowledge_sources", institution_id, knowledge_repo.ACTIVE_LIFECYCLE_STATUSES
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


def _academics_summary(db: Client, institution_id: UUID | str) -> DashboardAcademics:
    """Count academic records through institution-owned ``!inner`` joins."""
    return DashboardAcademics(
        attendance_records=_count_related(
            db,
            "student_attendance",
            "student_attendance_id",
            "students",
            institution_id,
        ),
        test_results=_count_related(
            db, "test_results", "test_result_id", "students", institution_id
        ),
        results=_count_related(
            db, "student_results", "student_result_id", "students", institution_id
        ),
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
        academics=_academics_summary(db, institution_id),
        quick_actions=list(QUICK_ACTIONS),
    )
