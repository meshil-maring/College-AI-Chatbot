"""Focused security contract for Phase 7.12 Super Admin authorization."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user, require_super_admin
from app.db.supabase import get_super_admin_authorization
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261001000000_phase_7_12_super_admin_identity_authorization.sql"
)
SCRIPT = Path(__file__).parents[2] / "scripts" / "validation" / "manage_local_super_admin.ps1"
LOCAL_SUPABASE_WRAPPER = (
    Path(__file__).parents[2] / "scripts" / "validation" / "invoke_local_supabase.ps1"
)


def _principal(role: str, *, institution_id: str | None = None) -> dict:
    return {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": "20000000-0000-0000-0000-000000000001",
        "email": "user@example.test",
        "roles": [role],
        "institution_id": institution_id,
        "status": "active",
    }


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_platform_endpoint_denies_anonymous_user() -> None:
    response = client.get("/api/v1/platform/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_auth_me_exposes_server_resolved_super_admin_role() -> None:
    principal = _principal("super_admin")
    with (
        patch(
            "app.core.security.verify_jwt",
            return_value={"sub": principal["auth_user_id"], "email": principal["email"]},
        ),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=principal),
        ),
    ):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer opaque.test.token"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "super_admin"


@pytest.mark.parametrize("role", ["student", "faculty", "staff", "admin"])
def test_platform_endpoint_denies_every_tenant_role(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal(role)
    response = client.get("/api/v1/platform/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_platform_endpoint_allows_only_platform_scoped_super_admin() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    ):
        response = client.get("/api/v1/platform/me")
    assert response.status_code == 200
    assert response.json() == {"role": "super_admin", "scope": "platform"}


def test_tenant_scoped_super_admin_grant_fails_closed() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal(
        "super_admin",
        institution_id="30000000-0000-0000-0000-000000000001",
    )
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": False}),
    ):
        response = client.get("/api/v1/platform/me")
    assert response.status_code == 403


def test_client_tenant_role_and_url_manipulation_cannot_escalate() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("admin")
    response = client.get(
        "/api/v1/platform/me",
        params={
            "role": "super_admin",
            "frontend_role": "super_admin",
            "institution_code": "OTHER-COLLEGE",
            "tenant_id": "00000000-0000-0000-0000-000000000099",
        },
        headers={"X-Role": "super_admin", "X-Institution-Code": "OTHER-COLLEGE"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_super_admin_does_not_inherit_tenant_admin_api() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_revocation_immediately_removes_platform_authorization() -> None:
    authorized = _principal("super_admin")
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    ):
        assert await require_super_admin(authorized) == authorized

    with (
        patch(
            "app.db.supabase.get_super_admin_authorization",
            new=AsyncMock(return_value={"status": "active", "has_platform_grant": False}),
        ),
        pytest.raises(AppError) as exc_info,
    ):
        await require_super_admin(authorized)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_inactive_account_is_denied_before_role_authorization() -> None:
    inactive = _principal("super_admin")
    app.dependency_overrides[get_current_user] = lambda: inactive
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "inactive", "has_platform_grant": True}),
    ):
        response = client.get(
            "/api/v1/platform/me",
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


@pytest.mark.asyncio
async def test_platform_authorization_read_requires_active_role_and_platform_scope() -> None:
    db = MagicMock()
    users = db.table.return_value
    users.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "status": "active",
        "user_roles": [
            {"scope_type": "institution", "roles": {"name": "super_admin", "is_active": True}},
            {"scope_type": "platform", "roles": {"name": "admin", "is_active": True}},
            {"scope_type": "platform", "roles": {"name": "super_admin", "is_active": False}},
        ],
    }
    with patch("app.db.supabase.get_admin_client", return_value=db):
        denied = await get_super_admin_authorization("auth-user")
    assert denied == {"status": "active", "has_platform_grant": False}

    users.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data[
        "user_roles"
    ].append(
        {"scope_type": "platform", "roles": {"name": "super_admin", "is_active": True}}
    )
    with patch("app.db.supabase.get_admin_client", return_value=db):
        allowed = await get_super_admin_authorization("auth-user")
    assert allowed == {"status": "active", "has_platform_grant": True}
    users.select.assert_called_with(
        "status, user_roles(scope_type, roles(name, is_active))"
    )


def test_migration_persists_role_scope_guard_audit_and_controlled_operations() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "INSERT INTO \"public\".\"roles\"" in sql
    assert "ON CONFLICT (\"name\") DO UPDATE" in sql
    assert "'super_admin'" in sql
    assert "trg_phase712_super_admin_scope" in sql
    assert "platform_role_audit_log" in sql
    assert "phase712_assign_super_admin" in sql
    assert "phase712_revoke_super_admin" in sql
    assert 'GRANT EXECUTE ON FUNCTION "public"."phase712_assign_super_admin"' in sql
    assert 'FROM PUBLIC, "anon", "authenticated"' in sql
    assert "auth.users" not in sql.lower()


def test_local_provisioner_is_explicit_fail_closed_and_secret_safe() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert '[ValidateSet("Assign", "Revoke")]' in script
    assert '[ValidateSet("local", "test")]' in script
    assert 'http://127.0.0.1:54321' in script
    assert "DOCKER_HOST" in script
    assert "SERVICE_ROLE_KEY=$" not in script
    assert "phase712_assign_super_admin" in script
    assert "phase712_revoke_super_admin" in script

    wrapper = LOCAL_SUPABASE_WRAPPER.read_text(encoding="utf-8")
    assert 'if ($Action -eq "status")' in wrapper
    assert 'Write-Output "LOCAL_STACK_STATUS=RUNNING"' in wrapper

