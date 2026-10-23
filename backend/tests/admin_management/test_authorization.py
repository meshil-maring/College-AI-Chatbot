from .support import (
    ADMIN_USER,
    MagicMock,
    STUDENT_USER,
    _ADMIN,
    _audit_db,
    admin_auth,
    app,
    client,
    get_current_user,
    patch,
    uuid4,
)


def test_admin_endpoint_requires_authentication() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_ADMIN, None)
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_endpoint_forbidden_for_non_admin_role() -> None:
    app.dependency_overrides.pop(_ADMIN, None)
    app.dependency_overrides[get_current_user] = lambda: STUDENT_USER
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_me_returns_identity_and_status() -> None:
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == ADMIN_USER["user_id"]
    assert body["email"] == ADMIN_USER["email"]
    assert body["roles"] == ["admin"]
    assert body["is_admin"] is True


def test_list_audit_logs_endpoint() -> None:
    entry = {"audit_id": str(uuid4()), "action": "faq.create", "table_name": "faqs"}
    with (
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
        patch("app.api.admin.audit.list_audit_entries", return_value=[entry]) as audit,
    ):
        response = client.get("/api/v1/admin/audit-logs?action=faq.create")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "faq.create"
    assert audit.call_args.kwargs["actor_user_id"] == ADMIN_USER["user_id"]


def test_get_audit_log_404_when_missing() -> None:
    db = _audit_db()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data=None
    )
    with patch("app.api.admin.common.get_admin_client", return_value=db):
        response = client.get(f"/api/v1/admin/audit-logs/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "AUDIT_NOT_FOUND"
