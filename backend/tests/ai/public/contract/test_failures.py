from .support import (
    MagicMock,
    RetrievalResponse,
    TestClient,
    _client_with_public_and_cross_tenant_chunks,
    _retrieval_results,
    app,
    httpx,
    patch,
    pytest,
)

def test_no_public_information_returns_safe_insufficient_context_response():
    fake = _client_with_public_and_cross_tenant_chunks()
    provider = MagicMock()
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.ai.public_chat.retrieve",
            return_value=RetrievalResponse(results=[]),
        ),
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "Unknown topic"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "answer": None,
        "status": "insufficient_context",
        "sources": [],
    }
    provider.generate.assert_not_called()

def test_generation_failure_returns_only_safe_provider_error():
    fake = _client_with_public_and_cross_tenant_chunks()
    provider = MagicMock()
    provider.generate.side_effect = RuntimeError("SECRET_API_KEY provider traceback")
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch("app.services.ai.public_chat.retrieve", return_value=_retrieval_results()),
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "PUBLIC_GENERATION_UNAVAILABLE",
            "message": "Public AI generation is temporarily unavailable.",
        }
    }
    assert "SECRET_API_KEY" not in response.text

def test_unhandled_retrieval_failure_uses_generic_error_envelope():
    fake = _client_with_public_and_cross_tenant_chunks()
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch(
            "app.services.ai.public_chat.retrieve",
            side_effect=RuntimeError("SELECT secret FROM internal_table"),
        ),
    ):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "SELECT" not in response.text
    assert "internal_table" not in response.text

@pytest.mark.parametrize("boundary", [
    "app.services.ai.public_chat.tenancy_repo.get_institution_by_code",
    "app.services.ai.public_chat.tenancy_repo.get_institution_by_id",
    "app.services.ai.public_chat.retrieve",
])
def test_database_connection_failure_is_retryable(boundary, caplog):
    fake = _client_with_public_and_cross_tenant_chunks()
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=fake),
        patch(boundary, side_effect=httpx.ConnectError("private database host and credentials")),
        patch("app.main.OpenRouterGenerationProvider") as provider,
    ):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": "COLLEGE001", "message": "What courses?"},
        )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.json() == {"error": {
        "code": "PUBLIC_CHAT_UNAVAILABLE",
        "message": "The chatbot is temporarily unavailable. Please try again shortly.",
    }}
    provider.return_value.generate.assert_not_called()
    assert "private database host and credentials" not in caplog.text
