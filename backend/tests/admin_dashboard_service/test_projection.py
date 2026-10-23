from .support import (
    MagicMock,
    _db,
    patch,
    svc,
    uuid4,
)


def test_dashboard_summary_bounds_recent_notices() -> None:
    """The dashboard is a summary: the recent list must stay bounded."""
    db = _db()
    with patch(
        "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
        return_value=[],
    ) as notices_mock:
        svc.get_dashboard_summary(
            institution_id=str(uuid4()),
            client=db,
            recent_notices_limit=3,
        )
    assert notices_mock.call_args.kwargs["limit"] == 3


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
        "app.services.admin.admin_dashboard.tenancy_repo.get_institution_by_id",
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
        "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
        return_value=rows,
    ):
        communication = svc._communication_summary(db, "inst-1", 5)
    assert communication.recent_notices[0].model_dump() == {
        "title": "Exam schedule",
        "category": "academic",
        "priority": "high",
        "published_at": "2026-01-01T00:00:00Z",
    }
