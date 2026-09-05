import json
from unittest.mock import patch

import httpx
import pytest

from app.services.embedding_provider import OPENROUTER_EMBEDDINGS_URL, OpenRouterEmbeddingProvider

MODEL = "qwen/qwen3-embedding-8b"
DIMENSIONS = 1536
API_KEY = "sk-or-secret"


def vector(value=0.1):
    return [value] * DIMENSIONS


def provider(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenRouterEmbeddingProvider(client), client


def test_success_request_contract():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [{"embedding": vector()}], "model": MODEL})

    instance, client = provider(handler)
    try:
        with patch("app.services.embedding_provider.settings.openrouter_api_key", API_KEY):
            result = instance.embed(["first chunk"])
    finally:
        client.close()

    request = requests[0]
    assert str(request.url) == OPENROUTER_EMBEDDINGS_URL
    assert request.method == "POST"
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert json.loads(request.content) == {
        "model": MODEL,
        "input": ["first chunk"],
        "dimensions": DIMENSIONS,
        "encoding_format": "float",
    }
    assert result == [vector()]


def test_batch_order_is_preserved():
    instance, client = provider(
        lambda request: httpx.Response(
            200, json={"data": [{"embedding": vector(0.1)}, {"embedding": vector(0.2)}]}
        )
    )
    try:
        result = instance.embed(["first", "second"])
    finally:
        client.close()
    assert result[0][0] == 0.1
    assert result[1][0] == 0.2


def test_count_mismatch_is_rejected():
    instance, client = provider(lambda request: httpx.Response(200, json={"data": []}))
    try:
        with pytest.raises(ValueError, match="count"):
            instance.embed(["input"])
    finally:
        client.close()


def test_dimension_mismatch_is_rejected():
    instance, client = provider(
        lambda request: httpx.Response(200, json={"data": [{"embedding": [0.1]}]})
    )
    try:
        with pytest.raises(ValueError, match="dimensions"):
            instance.embed(["input"])
    finally:
        client.close()


@pytest.mark.parametrize("payload", [{}, {"data": [{}]}, {"data": [{"embedding": "encoded"}]}])
def test_malformed_response_is_rejected(payload):
    instance, client = provider(lambda request: httpx.Response(200, json=payload))
    try:
        with pytest.raises(ValueError, match="malformed|dimensions"):
            instance.embed(["input"])
    finally:
        client.close()


def test_http_error_does_not_expose_secret():
    instance, client = provider(
        lambda request: httpx.Response(401, json={"error": {"message": API_KEY}})
    )
    try:
        with (
            patch("app.services.embedding_provider.settings.openrouter_api_key", API_KEY),
            pytest.raises(RuntimeError, match="401") as error,
        ):
            instance.embed(["input"])
    finally:
        client.close()
    assert API_KEY not in str(error.value)
