from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    STAFF_CLAIMS,
    _active_institution_authorization,
    _patch_staff_auth,
    client,
    resolve_primary_role,
)


def test_resolve_primary_role_returns_staff():
    assert resolve_primary_role(["staff"]) == "staff"


def test_auth_me_returns_staff_role_with_tenant():
    """Staff identity: canonical role + tenant resolved SERVER-SIDE."""
    with _patch_staff_auth():
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["role"] == "staff"
    assert body["institution_id"] == INSTITUTION_A
    assert body["email"] == STAFF_CLAIMS["email"]


def test_auth_me_client_role_claims_cannot_override_staff_role():
    """Client-supplied role/institution parameters never override /auth/me."""
    with _patch_staff_auth():
        response = client.get(
            "/api/v1/auth/me",
            headers=AUTH_HEADERS,
            params={"role": "admin", "institution_id": INSTITUTION_B},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "staff"
    assert body["institution_id"] == INSTITUTION_A
