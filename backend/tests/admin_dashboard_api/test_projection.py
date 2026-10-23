from .support import (
    ADMIN_A_USER,
    AUTH_HEADERS,
    EXPECTED_TOP_LEVEL,
    FORBIDDEN_KEYS,
    INST_B,
    _authenticated,
    _clean_dependencies,
    _dashboard_routes,
    _walk_keys,
    build_dashboard,
    client,
)


def test_response_model_reprojects_and_drops_stray_service_fields() -> None:
    """A service returning extra keys cannot widen the public contract.

    ``response_model=DashboardResponse`` re-projects the payload, so anything
    the service invents beyond the declared sections is dropped rather than
    forwarded to the client.
    """
    leaky_payload = {
        **build_dashboard().model_dump(),
        "service_role_key": "sk-live-should-never-appear",
        "institution_id": INST_B,
        "raw_rows": [{"secret": "value"}],
    }

    with _authenticated(
        ADMIN_A_USER, dashboard_response=lambda **_kwargs: leaky_payload
    ):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_TOP_LEVEL
    assert "sk-live-should-never-appear" not in response.text
    assert INST_B not in response.text
    assert "raw_rows" not in response.text


def test_response_contains_no_unexpected_internal_fields() -> None:
    """§18 — walk the whole payload; no key may be on the deny-list."""
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    body = response.json()
    assert set(body) == EXPECTED_TOP_LEVEL
    for key in _walk_keys(body):
        assert key not in FORBIDDEN_KEYS, f"forbidden key in dashboard: {key}"

    assert set(body["institution"]) == {"name", "code", "status"}
    assert set(body["students"]) == {"total", "pending_approvals", "approved", "active"}
    assert set(body["knowledge"]) == {
        "sources_total",
        "sources_active",
        "documents_total",
        "failed_processing_runs",
    }
    assert set(body["communication"]) == {
        "active_faqs",
        "active_notices",
        "recent_notices",
    }


def test_quick_actions_reference_existing_admin_capabilities() -> None:
    """Every quick action must be a real, already-implemented admin surface."""
    from app.services.admin.admin_dashboard import QUICK_ACTIONS

    existing_views = {
        "approvals",
        "students",
        "attendance",
        "results",
        "test-results",
        "notices",
        "documents",
        "faqs",
    }
    # Run the REAL service so the shipped quick actions are what is asserted.
    db = _RecordingClient()
    with _real_service(db):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    actions = response.json()["quick_actions"]
    assert len(actions) == len(QUICK_ACTIONS)
    assert actions, "quick actions must not be empty"
    for action in actions:
        assert set(action) == {"view", "label", "description"}
        assert action["view"] in existing_views
        assert action["label"] and action["description"]


def test_dashboard_route_declares_an_explicit_response_model() -> None:
    """§18 — explicit response schema, never an arbitrary row."""
    from app.schemas.admin.admin_dashboard import DashboardResponse

    (route,) = _dashboard_routes()
    assert route.response_model is DashboardResponse


from .database import _RecordingClient, _real_service
