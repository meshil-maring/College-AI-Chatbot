from collections.abc import Sequence
from threading import Lock
from typing import Protocol

import httpx

from app.config import settings


OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"

_shared_http_client: httpx.Client | None = None
_shared_http_client_lock = Lock()


def _get_shared_http_client() -> httpx.Client:
    """Return the process-wide HTTP client for embedding requests.

    Creating a new ``httpx.Client`` per embedding call forces a fresh TCP +
    TLS handshake against OpenRouter on every chat request. One shared client
    keeps connections pooled. ``httpx.Client`` is thread-safe; providers with
    an explicitly injected client (tests) never touch the shared instance.
    """
    global _shared_http_client
    with _shared_http_client_lock:
        if _shared_http_client is None:
            _shared_http_client = httpx.Client(timeout=60.0)
        return _shared_http_client


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class OpenRouterEmbeddingProvider:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name

        request_body = {
            "model": settings.embedding_model,
            "input": list(texts),
            "dimensions": settings.embedding_dimensions,
            "encoding_format": "float",
        }
        if self._client is None:
            response = _get_shared_http_client().post(
                OPENROUTER_EMBEDDINGS_URL,
                headers=headers,
                json=request_body,
            )
        else:
            response = self._client.post(
                OPENROUTER_EMBEDDINGS_URL,
                headers=headers,
                json=request_body,
            )
        if response.is_error:
            raise RuntimeError(f"OpenRouter embedding request failed ({response.status_code})")

        try:
            payload = response.json()
            data = payload["data"]
            vectors = [item["embedding"] for item in data]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("OpenRouter returned a malformed embedding response") from exc

        if len(vectors) != len(texts):
            raise ValueError("OpenRouter returned an embedding count that does not match the input count")
        for vector in vectors:
            if not isinstance(vector, list) or len(vector) != settings.embedding_dimensions:
                raise ValueError("OpenRouter returned an embedding with an unexpected number of dimensions")
        return vectors


_provider_instance: OpenRouterEmbeddingProvider | None = None
_provider_lock = Lock()


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider (one shared instance).

    The provider is stateless apart from its pooled HTTP client, so a single
    instance is safe to reuse across concurrent requests. Tests that need a
    specific provider patch this function itself.
    """
    global _provider_instance
    if settings.ai_provider != "openrouter":
        raise ValueError("Unsupported embedding provider")
    if not settings.openrouter_api_key:
        raise ValueError("OpenRouter API key is not configured")
    with _provider_lock:
        if _provider_instance is None:
            _provider_instance = OpenRouterEmbeddingProvider()
        return _provider_instance