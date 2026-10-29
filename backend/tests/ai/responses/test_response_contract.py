"""Responses: response contract."""

from .support import (
    CHUNK_A_ID,
    ChatUsage,
    GenerationProvider,
    GenerationResult,
    MagicMock,
    RetrievalResponse,
    SessionContext,
    TEST_USER_ID,
    UUID,
    _build_chat_usage,
    _chat_request,
    _mock_client,
    _process,
    patch,
    process_chat_request,
    uuid4,
)


def test_usage_mapping_from_metadata():
    """metadata["usage"] values are correctly mapped to ChatUsage."""
    metadata = {
        "provider": "openrouter",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        },
    }

    usage = _build_chat_usage(metadata)

    assert isinstance(usage, ChatUsage)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50


def test_missing_usage_returns_none():
    """Missing or empty usage data returns None without failure."""
    assert _build_chat_usage({}) is None
    assert _build_chat_usage({"usage": {}}) is None
    assert _build_chat_usage({"usage": {"prompt_tokens": 100}}) is not None
    assert _build_chat_usage(None) is None
    assert _build_chat_usage("not-a-dict") is None


def test_general_knowledge_uses_direct_generation_without_college_retrieval():
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="Quantum computing uses quantum-mechanical properties.",
        source_references=[],
        status="success",
        model_used="internal-model",
    )

    mc = _mock_client([
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
    ])

    request = _chat_request(user_query="What is quantum computing?")
    retrieval = RetrievalResponse(results=[])

    session_context = SessionContext(session_id=uuid4())
    with (
        patch("app.services.ai.chat.get_admin_client", return_value=mc),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mc),
        patch("app.services.ai.chat.retrieve", return_value=retrieval) as retrieve,
        patch("app.services.ai.chat._start_background_persistence"),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    retrieve.assert_not_called()
    mock_provider.generate.assert_called_once()
    assert response.status == "success"
    assert response.answer == "Quantum computing uses quantum-mechanical properties."
    assert response.message_id is not None
    assert response.source_references == []
    assert response.sources == []
    assert response.usage is None


def test_backward_compatibility_existing_fields_preserved():
    """All existing ChatResponse fields remain present and functional."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"According to [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"provider": "openrouter", "usage": {"prompt_tokens": 100, "completion_tokens": 50}},
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    # All original fields present
    assert hasattr(response, "session_id")
    assert hasattr(response, "conversation_id")
    assert hasattr(response, "message_id")
    assert hasattr(response, "answer")
    assert hasattr(response, "source_references")
    assert hasattr(response, "status")
    assert hasattr(response, "model_used")
    assert hasattr(response, "metadata")

    # source_references still populated from Phase 4.3 logic
    assert isinstance(response.source_references, list)
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # metadata still populated
    assert response.metadata["provider"] == "openrouter"
    assert "usage" in response.metadata

    # New fields also present
    assert isinstance(response.sources, list)
    assert isinstance(response.usage, ChatUsage)


def test_generation_provider_file_unchanged():
    """generation_provider.py must not have been modified for Phase 4.4."""
    import pathlib

    provider_path = pathlib.Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "generation_provider.py"
    content = provider_path.read_text(encoding="utf-8")

    # Verify key provider characteristics remain intact
    assert "class GenerationResult" in content
    assert "class GenerationProvider" in content
    assert "class OpenRouterGenerationProvider" in content
    assert "def generate(self, context: AIContext) -> GenerationResult:" in content

    # Verify provider does NOT contain Phase 4.4 structured response logic
    assert "StructuredSource" not in content
    assert "ChatUsage" not in content
    assert "_build_structured_sources" not in content
    assert "_enrich_source_titles" not in content
    assert "_build_chat_usage" not in content

    # Verify the model configuration is unchanged
    assert "openrouter" in content
    assert "openai/gpt-4o-mini" in content or "settings.openrouter_model" in content
