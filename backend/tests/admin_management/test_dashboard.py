from .support import (
    ADMIN_USER,
    DashboardRecentNotice,
    INSTITUTION_ID,
    UUID,
    admin_auth,
    build_dashboard,
    client,
    patch,
)


def test_dashboard_returns_typed_institution_scoped_payload() -> None:
    """Phase 7.21 — the endpoint serializes the explicit DashboardResponse.

    The legacy ``{counts, recent_audit}`` shape is gone: raw audit rows
    (actor_user_id / record_data / ip_address / user_agent) are internals and
    must never reach a dashboard client.
    """
    summary = build_dashboard(
        name="Alpha University",
        code="ALPHA",
        total_students=25,
        pending_approvals=3,
        approved=22,
        active_students=20,
        sources_total=4,
        sources_active=3,
        documents_total=11,
        active_faqs=7,
        active_notices=2,
    )
    with patch(
        "app.services.admin.admin_dashboard.get_dashboard_summary", return_value=summary
    ):
        response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["institution"] == {
        "name": "Alpha University",
        "code": "ALPHA",
        "status": "active",
    }
    assert body["students"] == {
        "total": 25,
        "pending_approvals": 3,
        "approved": 22,
        "active": 20,
    }
    assert body["communication"]["active_faqs"] == 7
    assert "recent_audit" not in body
    assert "counts" not in body


def test_dashboard_response_never_exposes_internal_identifiers() -> None:
    """Phase 7.21 §18 — no database/auth ids, no audit rows, no secrets."""
    summary = build_dashboard(
        total_students=1,
        recent_notices=[
            DashboardRecentNotice(
                title="Exam schedule",
                category="academic",
                priority="high",
                published_at="2026-01-01T00:00:00Z",
            )
        ],
    )
    with patch(
        "app.services.admin.admin_dashboard.get_dashboard_summary", return_value=summary
    ):
        response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 200
    raw = response.text
    for forbidden in (
        "institution_id",
        "user_id",
        "auth_user_id",
        "actor_user_id",
        "audit_id",
        "notice_id",
        "record_id",
        "record_data",
        "ip_address",
        "user_agent",
        "scope_type",
        "service_role",
        INSTITUTION_ID,
        ADMIN_USER["user_id"],
        ADMIN_USER["auth_user_id"],
    ):
        assert forbidden not in raw, f"dashboard leaked {forbidden!r}"


def test_dashboard_ignores_client_supplied_institution_id() -> None:
    """Phase 7.21 — the query parameter is gone; the server scope wins.

    An old client (or a hostile one) sending ``?institution_id=<other tenant>``
    must still receive its OWN institution's data, never the other tenant's.
    """
    summary = build_dashboard(name="Alpha University", code="ALPHA", total_students=7)
    other_tenant = "30000000-0000-0000-0000-0000000000ff"
    with patch(
        "app.services.admin.admin_dashboard.get_dashboard_summary", return_value=summary
    ) as svc:
        response = client.get(f"/api/v1/admin/dashboard?institution_id={other_tenant}")

    assert response.status_code == 200
    assert response.json()["institution"]["name"] == "Alpha University"
    assert svc.call_args.kwargs["institution_id"] == UUID(INSTITUTION_ID)
    assert other_tenant not in response.text
