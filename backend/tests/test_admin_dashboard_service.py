"""Phase Admin-3 tests — dashboard service."""

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


def _db():
    """Mock client returning per-table counts for 0/1/2 chained .eq() filters."""
    db = MagicMock()
    registry = {}

    def table(name):
        m = MagicMock()
        response = MagicMock(count=TABLE_COUNTS.get(name, 0), data=[])
        sel = m.select.return_value
        sel.execute.return_value = response
        eq1 = sel.eq.return_value
        eq1.execute.return_value = response
        eq1.eq.return_value.execute.return_value = response
        registry[name] = m
        return m

    db.table.side_effect = table
    db._registry = registry
    return db


def test_dashboard_summary_returns_counts_for_all_tables() -> None:
    db = _db()
    recent = [{"audit_id": str(uuid4()), "action": "faq.create"}]
    with patch("app.services.admin_dashboard.list_audit_entries", return_value=recent):
        summary = svc.get_dashboard_summary(client=db)

    assert summary["counts"]["knowledge_sources"] == 4
    assert summary["counts"]["documents"] == 11
    assert summary["counts"]["faqs"] == 7
    assert summary["counts"]["notices"] == 3
    assert summary["counts"]["students"] == 42
    assert summary["counts"]["student_results"] == 60
    assert summary["counts"]["test_results"] == 120
    assert summary["counts"]["attendance_records"] == 900
    assert summary["recent_audit"] == recent


def test_dashboard_summary_scopes_institution_owned_tables() -> None:
    db = _db()
    institution_id = str(uuid4())
    with patch("app.services.admin_dashboard.list_audit_entries", return_value=[]):
        svc.get_dashboard_summary(institution_id=institution_id, client=db)

    expected_scoped = {"knowledge_sources", "faqs", "notices", "students"}
    global_tables = {"documents", "student_results", "test_results", "student_attendance"}
    for name in expected_scoped:
        eq_args = [
            call.args
            for call in db._registry[name].select.return_value.eq.call_args_list
        ]
        assert ("institution_id", institution_id) in eq_args
    # is_active filter applied for faqs and notices (second .eq() in the chain)
    for name in ("faqs", "notices"):
        chained = db._registry[name].select.return_value.eq.return_value
        eq_args = [call.args for call in chained.eq.call_args_list]
        assert ("is_active", True) in eq_args
    # global (platform-wide) tables are not institution-scoped
    for name in global_tables:
        assert db._registry[name].select.return_value.eq.call_count == 0


def test_dashboard_summary_limits_recent_audit_entries() -> None:
    db = _db()
    with patch(
        "app.services.admin_dashboard.list_audit_entries", return_value=[]
    ) as audit_mock:
        svc.get_dashboard_summary(client=db, recent_audit_limit=5)
    audit_mock.assert_called_once_with(db, limit=5)


def test_count_returns_zero_when_count_missing() -> None:
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value = MagicMock(
        count=None, data=[]
    )
    assert svc._count(db, "faqs") == 0

