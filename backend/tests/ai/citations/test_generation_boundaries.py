"""Citations: generation boundaries."""

from .support import (
    GenerationProvider,
    GenerationResult,
    MagicMock,
    RetrievalResponse,
    SessionContext,
    TEST_USER_ID,
    _chat_request,
    _mock_client,
    _sync_background_persistence,
    patch,
    process_chat_request,
    uuid4,
)


def test_general_knowledge_skips_retrieval_and_creates_no_citations():
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


def test_generation_provider_keeps_persistence_outside_transport():
    """Structured evidence decoding must not acquire database responsibilities."""
    import pathlib

    provider_path = pathlib.Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "generation_provider.py"
    content = provider_path.read_text(encoding="utf-8")

    # Verify key provider characteristics remain intact
    assert "class GenerationResult" in content
    assert "class GenerationProvider" in content
    assert "class OpenRouterGenerationProvider" in content
    assert "def generate(self, context: AIContext) -> GenerationResult:" in content

    # Legacy text extraction and citation persistence remain outside transport.
    assert "message_citations" not in content
    assert "retrieval_operations" not in content
    assert "_extract_source_references" not in content

    # Verify the model configuration is unchanged
    assert "openrouter" in content
    assert "openai/gpt-4o-mini" in content or "settings.openrouter_model" in content
