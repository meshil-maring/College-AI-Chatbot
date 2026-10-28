from unittest.mock import MagicMock, patch

import pytest

from app.services.auth.identity import get_identity_institution_code

from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    SUPPORTED_ROLES,
    USER_ID,
    _patch_admin_auth,
    client,
    resolve_primary_role,
)


def test_resolve_primary_role_admin_precedence_unchanged():
    """admin > staff > faculty > student precedence is untouched."""
    assert resolve_primary_role(["admin"]) == "admin"
    assert resolve_primary_role(["student", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "super_admin"
    assert resolve_primary_role(["unknown-role"]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_returns_admin_role_with_tenant():
    """Admin identity: canonical role + tenant resolved SERVER-SIDE."""
    with _patch_admin_auth():
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "admin"
    assert body["institution_id"] == INSTITUTION_A
    assert body["institution_code"] == "ALPHA"


def test_auth_me_client_params_cannot_override_admin_role():
    """Client-supplied role/institution params never override /auth/me."""
    with _patch_admin_auth():
        response = client.get(
            "/api/v1/auth/me",
            headers=AUTH_HEADERS,
            params={
                "role": "student",
                "institution_id": INSTITUTION_B,
                "institution_code": "FORGED",
            },
        )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["institution_id"] == INSTITUTION_A
    assert response.json()["institution_code"] == "ALPHA"


def test_admin_responses_expose_no_token_material():
    with _patch_admin_auth():
        me = client.get("/api/v1/auth/me", headers=AUTH_HEADERS).json()
        admin_me = client.get("/api/v1/admin/me", headers=AUTH_HEADERS).json()
    forbidden = ("access_token", "refresh_token", "password", "jwt", "secret")
    for body in (me, admin_me):
        for key in body:
            assert key not in forbidden, key
    assert admin_me["user_id"] == USER_ID
    assert set(admin_me) == {"user_id", "auth_user_id", "email", "roles", "is_admin"}


def test_identity_code_uses_the_resolved_tenant_key():
    db = MagicMock()
    with (
        patch("app.services.auth.identity.get_admin_client", return_value=db),
        patch(
            "app.services.auth.identity.tenancy_repo.get_institution_by_id",
            return_value={"code": " ALPHA "},
        ) as get_institution,
    ):
        assert get_identity_institution_code({"institution_id": INSTITUTION_A}) == "ALPHA"
    get_institution.assert_called_once_with(db, INSTITUTION_A)


@pytest.mark.parametrize("institution", [None, {}, {"code": None}, {"code": "  "}])
def test_identity_code_is_unavailable_when_not_provided(institution):
    with (
        patch("app.services.auth.identity.get_admin_client"),
        patch(
            "app.services.auth.identity.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
    ):
        assert get_identity_institution_code({"institution_id": INSTITUTION_A}) is None


def test_identity_without_an_institution_does_not_query_the_database():
    with patch("app.services.auth.identity.get_admin_client") as get_db:
        assert get_identity_institution_code({"institution_id": None}) is None
    get_db.assert_not_called()
