from .support import (
    AUTH_HEADERS,
    AppError,
    TENANT_A,
    _active_institution_authorization,
    _assert_no_leak,
    _auth,
    _envelope,
    _user,
    client,
    patch,
    pytest,
    require_roles,
)


def test_malformed_scheme_is_401():
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Token abc"})
    assert r.status_code == 401
    assert _envelope(r)["code"] == "INVALID_SCHEME"


def test_staff_cannot_reach_admin_only_surface():
    with _auth("staff", TENANT_A):
        r = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert r.status_code == 403


def test_unauthenticated_admin_route_is_401_not_403():
    r = client.get("/api/v1/admin/dashboard")
    assert r.status_code == 401


def test_require_roles_denies_without_membership():
    import asyncio

    denied = require_roles("admin")
    with pytest.raises(AppError) as exc:
        asyncio.run(denied(current_user=_user("student", TENANT_A)))
    assert exc.value.status_code == 403


def test_dev_routes_hidden_outside_dev_mode():
    # The dev password-recovery router is gated at ROUTER level, so with
    # DEV_TEST_MODE=false every path answers a flat 404 (feature existence is
    # not disclosed) regardless of payload shape.
    with patch("app.api.auth.dev_auth.settings") as ms:
        ms.dev_test_mode = False
        for path in (
            "/api/v1/dev/auth/forgot-password",
            "/api/v1/dev/auth/change-password",
            "/api/v1/dev/auth/admin/reset-student-password",
        ):
            r = client.post(path, json={})
            assert r.status_code == 404
            assert _envelope(r)["code"] == "NOT_FOUND"
            _assert_no_leak(r.text)


def test_unhandled_exception_is_generic_500():
    with (
        patch(
            "app.main.resolve_session_context", side_effect=RuntimeError("SELECT boom")
        ),
        _auth("student", TENANT_A),
    ):
        r = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "Hi", "institution_id": TENANT_A},
        )
    assert r.status_code == 500
    assert _envelope(r)["code"] == "INTERNAL_ERROR"
    _assert_no_leak(r.text)
