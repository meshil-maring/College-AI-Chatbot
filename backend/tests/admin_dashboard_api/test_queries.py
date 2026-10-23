from .support import (
    AUTH_HEADERS,
    INACTIVE_ADMIN,
    INST_A,
    INST_B,
    _authenticated,
    _clean_dependencies,
    client,
    patch,
)


def test_inactive_account_is_denied() -> None:
    with _authenticated(INACTIVE_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_real_service_projects_recent_notices_without_identifiers() -> None:
    """End-to-end through the real service: no ids, no body content."""
    notice_rows = [
        {
            "notice_id": "secret-notice-id",
            "institution_id": INST_B,
            "title": "Exam schedule",
            "content": "internal body",
            "category": "academic",
            "priority": "high",
            "is_active": True,
            "is_published": True,
            "is_pinned": False,
            "published_at": "2026-01-01T00:00:00Z",
            "created_by": "secret-user-id",
        }
    ]
    db = _RecordingClient()
    with _real_service(db, notices=notice_rows):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert len(body["communication"]["recent_notices"]) == 1
    assert set(body["communication"]["recent_notices"][0]) == {
        "title",
        "category",
        "priority",
        "published_at",
    }
    assert "secret-notice-id" not in response.text
    assert "secret-user-id" not in response.text
    assert "internal body" not in response.text


def test_real_service_issues_bounded_queries_for_one_institution() -> None:
    """Performance: query count is fixed by the metric count, not the data size.

    Several metrics legitimately share a table (four student-status counts all
    read ``students``); what matters is that the count is CONSTANT regardless of
    how many rows the institution has, i.e. there is no per-row (N+1) query, and
    that every one of them carries the tenant filter.
    """
    db = _RecordingClient()
    # Capture the recent-notice call so the bound can be asserted.
    with (
        _real_service(db),
        patch(
            "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
            return_value=[],
        ) as notices_mock,
    ):
        first = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert "admin_audit_log" not in db.tables

    # Bounded: the recent-notice list is the only list read, and it is limited.
    assert notices_mock.call_args.kwargs["limit"] == 5

    # No repeated per-metric listing of students: the students table is only
    # ever COUNT-aggregated, never selected row-by-row.
    student_selects = [kwargs for name, _, kwargs in db.selects if name == "students"]
    assert student_selects, "expected student counts"
    assert all(kwargs.get("count") == "exact" for kwargs in student_selects), (
        student_selects
    )

    # Every directly-owned table carries the resolved tenant, and only that one.
    for name in ("students", "knowledge_sources", "faqs", "notices"):
        tenants = {f[1] for f in db.filters.get(name, []) if f[0] == "institution_id"}
        assert tenants == {INST_A}, (name, tenants)


from .database import _RecordingClient, _real_service
