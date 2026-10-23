from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    _active_institution_authorization,
    _assert_tenant_mismatch,
    _auth,
    client,
    patch,
    pytest,
)


@pytest.mark.parametrize("role", ["staff", "faculty"])
def test_institution_user_cannot_use_another_tenant_on_the_chat_contract(role: str):
    _assert_tenant_mismatch(
        role,
        "POST",
        "/api/v1/generation/chat",
        json={"user_query": "hello", "institution_id": INSTITUTION_B},
    )


@pytest.mark.parametrize("role", ["staff", "faculty"])
def test_inactive_institution_cannot_use_authenticated_chat(role: str):
    with (
        _auth(role),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value={
                "institution_id": INSTITUTION_A,
                "status": "suspended",
                "is_active": False,
            },
        ),
        patch("app.main.process_chat_request") as process_chat,
    ):
        response = client.post(
            "/api/v1/generation/chat",
            json={"user_query": "hello", "institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_INACTIVE"
    process_chat.assert_not_called()
