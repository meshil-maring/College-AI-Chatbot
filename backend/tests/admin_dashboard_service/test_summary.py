from .support import (
    _db,
    _no_notices,
    svc,
    uuid4,
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
