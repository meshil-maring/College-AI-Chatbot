"""Feature routers inherit the shared admin permission boundary."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.admin.dependencies import _ADMIN, _ADMIN_ROUTE_PERMISSIONS
from app.core.security import get_current_user
from app.main import app


@pytest.mark.parametrize(
    ("path", "handler"),
    [
        ("/dashboard", "app.services.admin.admin_dashboard.get_dashboard_summary"),
        ("/memberships", "app.services.admin.admin_memberships.list_roster"),
        ("/faqs", "app.services.admin.admin_faq.list_faqs"),
    ],
)
def test_missing_route_policy_blocks_feature_handler(monkeypatch, path, handler):
    actor = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "institution_id": "20000000-0000-0000-0000-000000000001",
        "roles": ["admin"],
        "status": "active",
        "permissions_resolved": True,
        "effective_permissions": ["*"],
    }
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[_ADMIN] = lambda: actor
    monkeypatch.delitem(_ADMIN_ROUTE_PERMISSIONS, ("GET", "/admin" + path))
    try:
        with patch(handler) as service:
            response = TestClient(app).get("/api/v1/admin" + path)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"
        service.assert_not_called()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
