from .support import (
    AUTH_HEADERS,
    AppError,
    MagicMock,
    STUDENT_A,
    STUDENT_B,
    TENANT_A,
    _active_institution_authorization,
    _assert_no_leak,
    _auth,
    _envelope,
    client,
    patch,
    pytest,
    uuid4,
)


def test_retrieval_forwards_caller_tenant():
    from app.schemas.knowledge.retrieval import RetrievalRequest
    from app.services.knowledge import retrieval as retrieval_svc

    captured = {}

    def _fake_search(query_embedding, *, top_k, institution_id=None, **kwargs):
        captured["institution_id"] = institution_id
        return []

    with (
        patch.object(retrieval_svc, "embed_query", return_value=[0.0] * 1536),
        patch.object(retrieval_svc, "search_chunks", side_effect=_fake_search),
    ):
        retrieval_svc.retrieve(RetrievalRequest(query="fees?", institution_id=TENANT_A))
    assert captured["institution_id"] == TENANT_A


def test_chat_requires_authentication():
    r = client.post(
        "/api/v1/generation/chat", json={"user_query": "Hi", "institution_id": TENANT_A}
    )
    assert r.status_code == 401


def test_provider_timeout_maps_to_safe_envelope():
    import httpx
    from app.schemas.ai.generation import AIContext
    from app.services.ai.generation_provider import OpenRouterGenerationProvider

    ctx = AIContext(
        user_question="fees?",
        system_instructions="sys",
        grounding_instructions="ground",
        retrieved_knowledge=[],
        conversation_history=[],
    )

    def _timeout(request):
        raise httpx.TimeoutException("timed out", request=request)

    provider = OpenRouterGenerationProvider(
        client=httpx.Client(transport=httpx.MockTransport(_timeout))
    )
    with patch("app.services.ai.generation_provider.settings") as ms:
        ms.openrouter_api_key = "k"
        ms.openrouter_model = "m"
        ms.openrouter_base_url = "https://openrouter.ai/api/v1"
        # The optional attribution headers must stay concrete strings: the
        # provider only sends them when configured, and a MagicMock here would
        # mask the timeout path with an httpx header TypeError.
        ms.openrouter_site_url = ""
        ms.openrouter_app_name = ""
        with pytest.raises(AppError) as exc:
            provider.generate(ctx)
    assert exc.value.code == "AI_PROVIDER_TIMEOUT"
    assert exc.value.status_code == 504


def test_rate_limit_maps_to_429_envelope():
    import httpx
    from app.schemas.ai.generation import AIContext
    from app.services.ai.generation_provider import OpenRouterGenerationProvider

    ctx = AIContext(
        user_question="q",
        system_instructions="sys",
        grounding_instructions="ground",
        retrieved_knowledge=[],
        conversation_history=[],
    )
    transport = httpx.MockTransport(lambda request: httpx.Response(429, json={}))
    provider = OpenRouterGenerationProvider(client=httpx.Client(transport=transport))
    with patch("app.services.ai.generation_provider.settings") as ms:
        ms.openrouter_api_key = "k"
        ms.openrouter_model = "m"
        ms.openrouter_base_url = "https://openrouter.ai/api/v1"
        ms.openrouter_site_url = ""
        ms.openrouter_app_name = ""
        with pytest.raises(AppError) as exc:
            provider.generate(ctx)
    assert exc.value.code == "AI_PROVIDER_RATE_LIMIT"
    assert exc.value.status_code == 429


def test_chat_generation_failure_is_safe_500():
    with (
        _auth("student", TENANT_A),
        patch("app.main.resolve_session_context", return_value=MagicMock()),
        patch(
            "app.main.process_chat_request",
            side_effect=AppError(
                "AI generation failed", status_code=500, code="GENERATION_FAILED"
            ),
        ),
    ):
        r = client.post(
            "/api/v1/generation/chat",
            headers=AUTH_HEADERS,
            json={"user_query": "Hello", "institution_id": TENANT_A},
        )
    assert r.status_code == 500
    assert _envelope(r)["code"] == "GENERATION_FAILED"
    _assert_no_leak(r.text)


def test_foreign_conversation_messages_are_404():
    from uuid import UUID
    from app.services.ai import conversation_history as history

    with (
        patch(
            "app.services.ai.conversation_history.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.ai.conversation_history.get_conversation",
            return_value={"conversation_id": "c", "user_id": STUDENT_B},
        ),
    ):
        with pytest.raises(AppError) as exc:
            history.get_conversation_messages(uuid4(), UUID(STUDENT_A))
    assert exc.value.status_code == 404
    assert exc.value.code == "CONVERSATION_NOT_FOUND"


def test_conversation_routes_require_authentication():
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.get(f"/api/v1/conversations/{uuid4()}/messages").status_code == 401


def test_user_a_cannot_read_user_b_conversation_via_api():
    other = str(uuid4())
    with (
        _auth("student", TENANT_A),
        patch(
            "app.services.ai.conversation_history.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.ai.conversation_history.get_conversation",
            return_value={"conversation_id": other, "user_id": STUDENT_B},
        ),
    ):
        r = client.get(f"/api/v1/conversations/{other}/messages", headers=AUTH_HEADERS)
    assert r.status_code == 404
    assert _envelope(r)["code"] == "CONVERSATION_NOT_FOUND"
