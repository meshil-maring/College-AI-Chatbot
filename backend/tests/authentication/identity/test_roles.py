"""Authentication identity regressions: roles."""

from __future__ import annotations

from .support import (
    MagicMock,
    patch,
    FAKE_USER,
    _patch_db,
    _patch_verify,
    client,
)


# ---------------------------------------------------------------------------
# Phase 6.15.4 — canonical identity contract on GET /auth/me
# ---------------------------------------------------------------------------

def test_auth_me_returns_admin_role():
    user = dict(FAKE_USER, roles=["admin"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["authenticated"] is True


def test_auth_me_returns_staff_role():
    user = dict(FAKE_USER, roles=["staff"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] == "staff"


def test_auth_me_returns_faculty_role():
    user = dict(
        FAKE_USER, roles=["faculty"], status="active",
        user_id="10000000-0000-0000-0000-000000000001",
        institution_id="30000000-0000-0000-0000-000000000001",
    )
    with (
        _patch_verify(), _patch_db(user=user),
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value={"status": "active", "is_active": True},
        ),
    ):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] == "faculty"


def test_auth_me_returns_student_role_with_tenant():
    """Student: role + tenant resolved in the correct institution context."""
    institution_id = "30000000-0000-0000-0000-000000000001"
    user = dict(FAKE_USER, roles=["student"], institution_id=institution_id)
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["institution_id"] == institution_id
    # Multi-role account: the canonical role is a single value.
    assert isinstance(body["role"], str)


def test_auth_me_resolves_highest_precedence_role_for_multi_role_account():
    """admin > staff > faculty > student precedence (existing RBAC preserved)."""
    from app.core.security import resolve_primary_role

    assert resolve_primary_role(["student", "admin"]) == "admin"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["student", "faculty"]) == "faculty"
    assert resolve_primary_role(["student"]) == "student"


def test_auth_me_unknown_role_resolves_to_none_fail_safe():
    """A role outside the supported set must never surface as privileged."""
    from app.core.security import resolve_primary_role

    user = dict(FAKE_USER, roles=["superuser"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] is None
    assert resolve_primary_role(["superuser", "root"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_ignores_client_provided_role_or_tenant_data():
    """Security: query/body data can never influence the resolved role.

    The role comes only from the server-side user_roles chain; extra query
    parameters are ignored (no injection surface), and the response role is
    derived exclusively from the authenticated identity.
    """
    user = dict(FAKE_USER, roles=["student"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid.token.here"},
            params={"role": "admin", "institution_id": "00000000-0000-0000-0000-000000000099"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["institution_id"] != "00000000-0000-0000-0000-000000000099"


def test_auth_me_unauthenticated_rejected_preserved():
    """Regression: the unauthenticated 401 AUTH_REQUIRED contract is intact."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ---------------------------------------------------------------------------
# Health check remains public
# ---------------------------------------------------------------------------

def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
