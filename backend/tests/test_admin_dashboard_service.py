"""Phase 7.21 — dashboard service.

The Phase 7.20 guarantees are preserved and extended: every count is scoped to
the authoritative institution (directly, or through an ``!inner`` join to an
institution-owned parent), and the audit feed has been REMOVED because raw
``admin_audit_log`` rows are internals the dashboard must not expose.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services import admin_dashboard as svc

TABLE_COUNTS = {
    "knowledge_sources": 4,
    "documents": 11,
    "faqs": 7,
    "notices": 3,
    "students": 42,
    "student_results": 60,
    "test_results": 120,
    "student_attendance": 900,
}


def _db(counts: dict[str, int] | None = None):
    """Mock client returning per-table counts for chained .eq()/.in_() filters."""
    counts = TABLE_COUNTS if counts is None else counts
    db = MagicMock()
    registry = {}

    def table(name):
        m = MagicMock()
        response = MagicMock(count=counts.get(name, 0), data=[])
        sel = m.select.return_value
        sel.execute.return_value = response
        eq1 = sel.eq.return_value
        eq1.execute.return_value = response
        eq1.eq.return_value.execute.return_value = response
        eq1.in_.return_value.execute.return_value = response
        registry[name] = m
        return m

    db.table.side_effect = table
    db._registry = registry
    return db


def _no_notices():
    """Stub the shared notice-listing repository used for recent notices."""
    return patch(
        "app.services.admin_dashboard.knowledge_repo.list_notices",
        return_value=[],
    )


def test_dashboard_summary_returns_all_section_metrics() -> None:
    db = _db()
    with _no_notices():
        summary = svc.get_dashboard_summary(institution_id=str(uuid4()), client=db)

    assert summary.students.total == 42
    assert summary.knowledge.sources_total == 4
    assert summary.knowledge.documents_total == 11
    assert summary.communication.active_faqs == 7
    assert summary.communication.active_notices == 3
    assert summary.academics.results == 60
    assert summary.academics.test_results == 120
    assert summary.academics.attendance_records == 900


def test_dashboard_summary_scopes_every_institution_owned_count() -> None:
    """The core tenant guarantee: no count may run without the tenant filter."""
    db = _db()
    institution_id = str(uuid4())
    with _no_notices():
        svc.get_dashboard_summary(institution_id=institution_id, client=db)

    # Every table queried directly must carry the institution filter.
    for name in ("knowledge_sources", "faqs", "notices", "students"):
        eq_args = [
            call.args
            for call in db._registry[name].select.return_value.eq.call_args_list
        ]
        assert ("institution_id", institution_id) in eq_args, name

    # is_active filter applied for faqs and notices (chained .eq()).
    for name in ("faqs", "notices"):
        chained = db._registry[name].select.return_value.eq.return_value
        assert ("is_active", True) in [call.args for call in chained.eq.call_args_list]

    # Related tables resolve the tenant through an !inner join, never a direct
    # unscoped count.
    related_scopes = {
        "documents": "knowledge_sources.institution_id",
        "student_results": "students.institution_id",
        "test_results": "students.institution_id",
        "student_attendance": "students.institution_id",
    }
    for name, field in related_scopes.items():
        db._registry[name].select.return_value.eq.assert_called_once_with(
            field, institution_id
        )


def test_dashboard_summary_bounds_recent_notices() -> None:
    """The dashboard is a summary: the recent list must stay bounded."""
    db = _db()
    with patch(
        "app.services.admin_dashboard.knowledge_repo.list_notices",
        return_value=[],
    ) as notices_mock:
        svc.get_dashboard_summary(
            institution_id=str(uuid4()),
            client=db,
            recent_notices_limit=3,
        )
    assert notices_mock.call_args.kwargs["limit"] == 3


def test_dashboard_summary_never_reads_the_audit_log() -> None:
    """Phase 7.21 §18 — raw audit rows are internals and are not queried."""
    db = _db()
    with _no_notices():
        svc.get_dashboard_summary(institution_id=str(uuid4()), client=db)
    queried = [call.args[0] for call in db.table.call_args_list if call.args]
    assert "admin_audit_log" not in queried


def test_failed_processing_runs_is_reported_as_unavailable_not_zero() -> None:
    """A metric the schema cannot resolve must be null, never a fabricated 0."""
    db = _db()
    with _no_notices():
        summary = svc.get_dashboard_summary(institution_id=str(uuid4()), client=db)
    assert summary.knowledge.failed_processing_runs is None


def test_quick_actions_only_name_existing_admin_views() -> None:
    """Every quick action must point at a screen that already exists."""
    valid_views = {
        "dashboard",
        "approvals",
        "students",
        "attendance",
        "results",
        "test-results",
        "notices",
        "documents",
        "faqs",
        "assistant",
        "profile",
    }
    assert svc.QUICK_ACTIONS
    for action in svc.QUICK_ACTIONS:
        assert action.view in valid_views, action.view


def test_zero_data_institution_returns_zeroes_not_errors() -> None:
    """A brand-new institution must render, with zeros, not fail."""
    db = _db(counts={})
    with _no_notices():
        summary = svc.get_dashboard_summary(institution_id=str(uuid4()), client=db)
    assert summary.students.total == 0
    assert summary.knowledge.documents_total == 0
    assert summary.communication.active_faqs == 0
    assert summary.academics.results == 0
    assert summary.communication.recent_notices == []


def test_institution_summary_projects_only_safe_display_fields() -> None:
    """Only name/code/status; no ids, no contact details, no platform config."""
    institution_id = str(uuid4())
    db = MagicMock()
    row = {
        "institution_id": institution_id,
        "organization_id": "org-1",
        "name": "Alpha University",
        "code": "ALPHA",
        "email": "admin@alpha.edu",
        "address": "1 College Road",
        "status": "active",
        "is_active": True,
    }
    with patch(
        "app.services.admin_dashboard.tenancy_repo.get_institution_by_id",
        return_value=row,
    ) as read_mock:
        institution = svc._institution_summary(db, institution_id)
    read_mock.assert_called_once_with(db, institution_id)
    assert institution.model_dump() == {
        "name": "Alpha University",
        "code": "ALPHA",
        "status": "active",
    }


def test_recent_notices_are_projected_without_identifiers() -> None:
    db = MagicMock()
    rows = [
        {
            "notice_id": "n-1",
            "institution_id": "inst-1",
            "title": "Exam schedule",
            "content": "long body",
            "category": "academic",
            "priority": "high",
            "is_active": True,
            "is_published": True,
            "is_pinned": False,
            "published_at": "2026-01-01T00:00:00Z",
            "created_by": "u-1",
        }
    ]
    with patch(
        "app.services.admin_dashboard.knowledge_repo.list_notices", return_value=rows
    ):
        communication = svc._communication_summary(db, "inst-1", 5)
    assert communication.recent_notices[0].model_dump() == {
        "title": "Exam schedule",
        "category": "academic",
        "priority": "high",
        "published_at": "2026-01-01T00:00:00Z",
    }


def test_count_returns_zero_when_count_missing() -> None:
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value = MagicMock(
        count=None, data=[]
    )
    assert svc._count(db, "faqs") == 0


def test_related_count_uses_inner_tenant_relationship() -> None:
    db = MagicMock()
    response = MagicMock(count=7, data=[])
    chain = db.table.return_value.select.return_value
    chain.eq.return_value.execute.return_value = response
    institution_id = str(uuid4())

    assert (
        svc._count_related(
            db,
            "documents",
            "document_id",
            "knowledge_sources",
            institution_id,
        )
        == 7
    )
    db.table.assert_called_once_with("documents")
    db.table.return_value.select.assert_called_once_with(
        "document_id, knowledge_sources!inner(institution_id)", count="exact"
    )
    chain.eq.assert_called_once_with("knowledge_sources.institution_id", institution_id)


def test_count_in_applies_tenant_filter_on_the_same_query() -> None:
    """The ``in_`` variant must not drop the institution scoping."""
    db = MagicMock()
    response = MagicMock(count=3, data=[])
    chain = db.table.return_value.select.return_value
    chain.eq.return_value.in_.return_value.execute.return_value = response
    institution_id = str(uuid4())

    assert svc._count_in(db, "knowledge_sources", institution_id, ["published"]) == 3
    chain.eq.assert_called_once_with("institution_id", institution_id)
    chain.eq.return_value.in_.assert_called_once_with(
        "lifecycle_status", ["published"]
    )

