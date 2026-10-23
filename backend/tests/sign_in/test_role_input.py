"""Test role input."""

from __future__ import annotations

from uuid import UUID, uuid4

from .credentials import (
    login_api,
)

from .identity import (
    _active_institution_authorization,
    _as_authenticated,
    _auth_user,
    _login_payload,
)

from .support import (
    ACCOUNT_PASSWORD,
    APPROVED_EMAIL,
    FAKE_CLAIMS,
    INSTITUTION_A,
    LOGIN_URL,
    STUDENT_LOGIN_URL,
    client,
    student_account,
)


def test_16_role_cannot_be_overridden_on_email_login():
    response = client.post(
        LOGIN_URL,
        json={"email": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD, "role": "admin"},
    )
    assert response.status_code == 422, response.text


def test_16b_role_cannot_be_overridden_on_student_login():
    response = client.post(
        STUDENT_LOGIN_URL,
        json={
            "identifier": APPROVED_EMAIL,
            "password": ACCOUNT_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 422, response.text


def test_16c_other_authorization_fields_cannot_be_overridden():
    for field, value in (
        ("roles", ["admin"]),
        ("status", "active"),
        ("approval_status", "approved"),
        ("is_admin", True),
        ("user_id", str(uuid4())),
        ("auth_user_id", str(uuid4())),
    ):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = value
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_16d_login_response_never_echoes_role_or_scope():
    response = login_api(account=student_account())
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "message",
        "user",
    }
    assert set(body["user"].keys()) == {"id", "email"}


def test_16e_self_declared_role_is_ignored_by_rbac():
    """A client-declared role has no effect: RBAC reads trusted records."""
    user = {"user_id": uuid4(), "auth_user_id": FAKE_CLAIMS["sub"], "email": "x@c.edu"}
    projection = _auth_user(user, roles=(), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            "/api/v1/admin/me",
            headers={"Authorization": "Bearer valid.token.here", "X-Role": "admin"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"
