"""Test platform."""

from __future__ import annotations

from app.core.security import get_current_user

from app.main import app

from unittest.mock import AsyncMock, MagicMock, patch

from .support import (
    _clean_dependencies,
    client,
    conflicting_admin,
)


def test_super_admin_platform_authorization_regression_is_unchanged() -> None:
    super_admin = {
        "user_id": "76000000-0000-0000-0000-000000000001",
        "auth_user_id": "76000000-0000-0000-0000-000000000002",
        "email": "super@example.edu",
        "roles": ["super_admin"],
        "status": "active",
        "institution_id": None,
        "role_assignments": [
            {
                "role": "super_admin",
                "scope_type": "platform",
                "scope_id": None,
                "is_active": True,
            }
        ],
    }
    app.dependency_overrides[get_current_user] = lambda: super_admin
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    ):
        platform = client.get("/api/v1/platform/me")
        admin = client.get("/api/v1/admin/me")
    assert platform.status_code == 200
    assert admin.status_code == 403
