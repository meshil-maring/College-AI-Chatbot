from .support import (
    _db,
    _no_notices,
    svc,
    uuid4,
)


def test_zero_data_institution_returns_zeroes_not_errors() -> None:
    """A brand-new institution must render, with zeros, not fail."""
    db = _db(counts={})
    with _no_notices():
        summary = svc.get_dashboard_summary(institution_id=str(uuid4()), client=db)
    assert summary.students.total == 0
    assert summary.knowledge.documents_total == 0
    assert summary.communication.active_faqs == 0
    assert summary.communication.recent_notices == []
