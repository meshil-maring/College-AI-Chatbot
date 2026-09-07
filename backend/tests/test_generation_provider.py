import json
from uuid import UUID
from unittest.mock import patch

import httpx
import pytest

from app.core.errors import AppError
from app.config import Settings
from app.schemas.generation import AIContext, RetrievedChunk
from app.services.generation_provider import OpenRouterGenerationProvider

API_KEY = "test-openrouter-key"
MODEL = "openai/gpt-4o-mini"
BASE_URL = "https://openrouter.example/api/v1"


def context() -> AIContext:
    return AIContext(
        system_instructions="Use only supplied college knowledge.",
        user_question="What are the admissions requirements?",
        retrieved_knowledge=[
            RetrievedChunk(
                chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
                text="A completed application is required.",
                similarity_score=0.9,
                metadata={"section": "Admissions"},
            )
        ],
        grounding_instructions="Cite only retrieved chunks and never invent sources.",
    )


def provider(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenRouterGenerationProvider(client), client


def configured():
    return patch.multiple(
        "app.services.generation_provider.settings",
        openrouter_api_key=API_KEY,
        openrouter_model=MODEL,
        openrouter_base_url=BASE_URL,
    )


def test_demo_configuration_defaults():
    demo_settings = Settings(_env_file=None)

    assert demo_settings.openrouter_model == MODEL
    assert demo_settings.openrouter_base_url == "https://openrouter.ai/api/v1"


def test_api_key_is_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", API_KEY)

    environment_settings = Settings(_env_file=None)

    assert environment_settings.openrouter_api_key == API_KEY


def test_request_preserves_context_and_configuration():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"model": MODEL, "choices": [{"message": {"content": "Apply online."}}]},
        )

    instance, client = provider(handler)
    try:
        with configured():
            result = instance.generate(context())
    finally:
        client.close()

    request = requests[0]
    payload = json.loads(request.content)
    assert str(request.url) == f"{BASE_URL}/chat/completions"
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert payload["model"] == MODEL
    system_content = payload["messages"][0]["content"]
    user_content = payload["messages"][1]["content"]
    assert "Use only supplied college knowledge." in system_content
    assert "Cite only retrieved chunks" in system_content
    assert "What are the admissions requirements?" in user_content
    assert "A completed application is required." in user_content
    assert "00000000-0000-0000-0000-000000000001" in user_content
    assert result.answer == "Apply online."
    assert result.model_used == MODEL
    assert result.source_references == []


def test_provider_does_not_perform_source_reference_extraction():
    """Provider returns empty source_references regardless of explicit chunk references in the answer.

    Source-reference extraction is the responsibility of the chat orchestration layer,
    not the generation provider.
    """
    chunk = context().retrieved_knowledge[0]
    instance, client = provider(
        lambda _request: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": f"The requirement is documented in [Retrieved chunk {chunk.chunk_id}]."
                        }
                    }
                ]
            },
        )
    )
    try:
        with configured():
            result = instance.generate(context())
    finally:
        client.close()

    assert result.source_references == []
    assert result.answer is not None
    assert str(chunk.chunk_id) in result.answer


def test_context_model_name_overrides_configured_default():
    requests = []
    instance, client = provider(
        lambda request: (
            requests.append(request)
            or httpx.Response(200, json={"choices": [{"message": {"content": "Answer"}}]})
        )
    )
    requested_context = context().model_copy(update={"model_name": "custom/model"})
    try:
        with configured():
            instance.generate(requested_context)
    finally:
        client.close()

    assert json.loads(requests[0].content)["model"] == "custom/model"


def test_missing_api_key_is_rejected_without_request():
    def fail(_request):
        raise AssertionError("request must not be sent")

    instance, client = provider(fail)
    try:
        with (
            patch.multiple(
                "app.services.generation_provider.settings",
                openrouter_api_key="",
                openrouter_model=MODEL,
                openrouter_base_url=BASE_URL,
            ),
            pytest.raises(AppError, match="API key is not configured") as error,
        ):
            instance.generate(context())
    finally:
        client.close()
    assert error.value.code == "AI_PROVIDER_CONFIGURATION_ERROR"


@pytest.mark.parametrize("field", ["openrouter_model", "openrouter_base_url"])
def test_invalid_configuration_is_rejected(field):
    instance, client = provider(lambda _request: httpx.Response(200))
    values = {"openrouter_api_key": API_KEY, "openrouter_model": MODEL, "openrouter_base_url": BASE_URL}
    values[field] = "invalid" if field == "openrouter_base_url" else ""
    try:
        with patch.multiple("app.services.generation_provider.settings", **values):
            with pytest.raises(AppError) as error:
                instance.generate(context())
    finally:
        client.close()
    assert error.value.code == "AI_PROVIDER_CONFIGURATION_ERROR"


@pytest.mark.parametrize("status", [400, 401, 500])
def test_http_errors_do_not_expose_key(status):
    instance, client = provider(
        lambda _request: httpx.Response(status, json={"error": {"message": API_KEY}})
    )
    try:
        with configured(), pytest.raises(AppError) as error:
            instance.generate(context())
    finally:
        client.close()
    assert API_KEY not in str(error.value)
    assert error.value.code in {
        "AI_PROVIDER_ERROR",
        "AI_PROVIDER_AUTHENTICATION_ERROR",
    }


def test_timeout_is_mapped():
    instance, client = provider(lambda _request: (_ for _ in ()).throw(httpx.ReadTimeout("timeout")))
    try:
        with configured(), pytest.raises(AppError) as error:
            instance.generate(context())
    finally:
        client.close()
    assert error.value.code == "AI_PROVIDER_TIMEOUT"
    assert error.value.status_code == 504


def test_network_failure_is_mapped():
    instance, client = provider(lambda _request: (_ for _ in ()).throw(httpx.ConnectError("offline")))
    try:
        with configured(), pytest.raises(AppError) as error:
            instance.generate(context())
    finally:
        client.close()
    assert error.value.code == "AI_PROVIDER_NETWORK_ERROR"


@pytest.mark.parametrize(
    "payload",
    [{}, {"choices": []}, {"choices": [{"message": {}}]}, {"choices": [{"message": {"content": ""}}]}],
)
def test_malformed_or_empty_response_is_rejected(payload):
    instance, client = provider(lambda _request: httpx.Response(200, json=payload))
    try:
        with configured(), pytest.raises(AppError, match="response") as error:
            instance.generate(context())
    finally:
        client.close()
    assert error.value.code == "AI_PROVIDER_RESPONSE_ERROR"
