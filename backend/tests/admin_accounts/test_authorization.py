from .support import (
    AUTH_HEADERS,
    _patch_admin_auth,
    client,
)


def test_admin_me_returns_identity_and_status():
    with _patch_admin_auth():
        response = client.get("/api/v1/admin/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
