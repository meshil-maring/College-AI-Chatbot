from .support import (
    ADMIN_A_USER,
    ADMIN_B_USER,
    AUTH_HEADERS,
    INST_A,
    INST_B,
    TENANTLESS_ADMIN,
    UUID,
    _authenticated,
    _clean_dependencies,
    _dashboard_routes,
    build_dashboard,
    client,
    pytest,
)


def test_admin_a_receives_institution_a_metrics() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["institution"] == {
        "name": "Alpha University",
        "code": "ALPHA",
        "status": "active",
    }
    assert body["students"]["total"] == 11


def test_admin_b_receives_institution_b_metrics() -> None:
    with _authenticated(ADMIN_B_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["institution"] == {
        "name": "Beta Institute",
        "code": "BETA",
        "status": "active",
    }
    assert body["students"]["total"] == 77


def test_admin_a_cannot_see_institution_b_data() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    raw = response.text
    for leak in ("Beta Institute", "BETA", INST_B, "77", "909", "707"):
        assert leak not in raw, f"Admin A dashboard leaked {leak!r}"


def test_admin_b_cannot_see_institution_a_data() -> None:
    with _authenticated(ADMIN_B_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    raw = response.text
    for leak in ("Alpha University", "ALPHA", INST_A, "11", "303", "101"):
        assert leak not in raw, f"Admin B dashboard leaked {leak!r}"


def test_service_only_ever_receives_the_authorized_tenant() -> None:
    """The API layer hands the service exactly the resolved institution."""
    with _authenticated(ADMIN_A_USER) as service:
        client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        assert service.call_args.kwargs["institution_id"] == UUID(INST_A)
    with _authenticated(ADMIN_B_USER) as service:
        client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        assert service.call_args.kwargs["institution_id"] == UUID(INST_B)


@pytest.mark.parametrize(
    "params",
    [
        {"institution_id": INST_B},
        {"institution_id": INST_B, "role": "super_admin"},
        {"scope_type": "platform"},
        {"institution_code": "BETA"},
        {"code": "BETA"},
        {"tenant": INST_B},
    ],
)
def test_client_supplied_institution_values_never_alter_scope(params) -> None:
    """Phase 7.21 §9 — a foreign tenant in ANY parameter changes nothing.

    The parameter no longer exists on the endpoint, so FastAPI ignores it. The
    response is byte-for-byte Admin A's own dashboard either way.
    """
    with _authenticated(ADMIN_A_USER):
        clean = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
        manipulated = client.get(
            "/api/v1/admin/dashboard", headers=AUTH_HEADERS, params=params
        )
    assert clean.status_code == 200
    assert manipulated.status_code == 200
    assert manipulated.json() == clean.json()
    assert manipulated.json()["institution"]["code"] == "ALPHA"


def test_foreign_institution_id_is_never_echoed_back() -> None:
    with _authenticated(ADMIN_A_USER):
        response = client.get(
            f"/api/v1/admin/dashboard?institution_id={INST_B}", headers=AUTH_HEADERS
        )
    assert INST_B not in response.text


def test_tenantless_admin_is_denied() -> None:
    with _authenticated(TENANTLESS_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in ("SCOPE_MISSING", "SCOPE_INCONSISTENT")


def test_inactive_institution_is_denied() -> None:
    with _authenticated(ADMIN_A_USER, institution_active=False):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_INACTIVE"


def test_zero_data_institution_renders_successfully() -> None:
    """0 students / 0 documents / 0 FAQs / 0 notices is a normal 200, not an error."""
    empty = build_dashboard(name="Fresh University", code="FRESH", status="active")

    def _empty(*, institution_id, **kwargs):
        assert str(institution_id) == INST_B
        return empty

    with _authenticated(ADMIN_B_USER, dashboard_response=_empty):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["students"] == {
        "total": 0,
        "pending_approvals": 0,
        "approved": 0,
        "active": 0,
    }
    assert body["knowledge"]["documents_total"] == 0
    assert body["knowledge"]["failed_processing_runs"] is None
    assert body["communication"]["active_faqs"] == 0
    assert body["communication"]["active_notices"] == 0
    assert body["communication"]["recent_notices"] == []


def test_dashboard_route_accepts_no_institution_parameter() -> None:
    """§6 — no client-supplied tenant exists for the dashboard to read."""
    (route,) = _dashboard_routes()
    query_params = {param.name for param in route.dependant.query_params}
    assert "institution_id" not in query_params
    assert query_params == set()
