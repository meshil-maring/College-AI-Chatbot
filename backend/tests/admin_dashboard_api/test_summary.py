from .support import (
    ADMIN_A_USER,
    AUTH_HEADERS,
    _authenticated,
    _clean_dependencies,
    _dashboard_routes,
    app,
    client,
)


def test_internal_dashboard_error_is_normalized() -> None:
    """A backend blow-up must surface as the project's safe 500 envelope."""

    def _explode(**_kwargs):
        raise RuntimeError(
            "connection to server at 10.0.0.5 failed: SELECT * FROM students"
        )

    with _authenticated(ADMIN_A_USER, dashboard_response=_explode):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "SELECT" not in response.text
    assert "10.0.0.5" not in response.text
    assert "students" not in response.text


def test_dashboard_is_the_only_dashboard_endpoint() -> None:
    """§5 — one coherent dashboard response, not several competing ones."""
    routes = _dashboard_routes()
    assert len(routes) == 1
    assert routes[0].path == "/admin/dashboard"
    # And the OpenAPI document publishes exactly one dashboard path.
    published = [
        path
        for path in app.openapi()["paths"]
        if "dashboard" in path and path.startswith("/api/v1/admin")
    ]
    assert published == ["/api/v1/admin/dashboard"]
