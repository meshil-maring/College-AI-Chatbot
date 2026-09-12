from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.core.errors import AppError
from app.schemas.generation import AIContext, SourceReference


_shared_http_client: httpx.Client | None = None
_shared_http_client_lock = Lock()


def _get_shared_http_client() -> httpx.Client:
    """Return the process-wide HTTP client for OpenRouter requests.

    Building a new ``httpx.Client`` per request forces a fresh TCP + TLS
    handshake against the provider on every chat message. One shared client
    keeps connections pooled across requests. ``httpx.Client`` is thread-safe,
    and providers that receive an explicitly injected client (tests use mock
    transports) never touch the shared instance.
    """
    global _shared_http_client
    with _shared_http_client_lock:
        if _shared_http_client is None:
            _shared_http_client = httpx.Client(timeout=60.0)
        return _shared_http_client


class GenerationResult:
    """Provider-neutral result returned by an AI generation provider."""

    def __init__(
        self,
        *,
        answer: str | None = None,
        source_references: list[SourceReference] | None = None,
        status: str = "success",
        model_used: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.answer = answer
        self.source_references = source_references or []
        self.status = status
        self.model_used = model_used
        self.metadata = metadata or {}


class GenerationProvider(Protocol):
    def generate(self, context: AIContext) -> GenerationResult:
        """Generate from the supplied context without performing retrieval."""


class OpenRouterGenerationProvider:
    """Generate responses through OpenRouter's chat completions API."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = client
        self._timeout = timeout

    def generate(self, context: AIContext) -> GenerationResult:
        if not isinstance(context, AIContext):
            raise TypeError("context must be a validated AIContext")

        api_key = settings.openrouter_api_key.strip()
        model = (context.model_name or settings.openrouter_model).strip()
        base_url = settings.openrouter_base_url.strip().rstrip("/")
        if not api_key:
            raise AppError(
                "OpenRouter API key is not configured",
                status_code=500,
                code="AI_PROVIDER_CONFIGURATION_ERROR",
            )
        if not model or not _is_http_url(base_url):
            raise AppError(
                "OpenRouter model or base URL configuration is invalid",
                status_code=500,
                code="AI_PROVIDER_CONFIGURATION_ERROR",
            )

        request_body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{context.system_instructions}\n\n"
                        "Grounding and citation instructions:\n"
                        f"{context.grounding_instructions}"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_user_content(context),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_name:
            headers["X-Title"] = settings.openrouter_app_name

        try:
            if self._client is None:
                response = _get_shared_http_client().post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )
            else:
                response = self._client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )
        except httpx.TimeoutException as exc:
            raise AppError(
                "OpenRouter request timed out",
                status_code=504,
                code="AI_PROVIDER_TIMEOUT",
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "OpenRouter request failed",
                status_code=502,
                code="AI_PROVIDER_NETWORK_ERROR",
            ) from exc

        if response.status_code in {401, 403}:
            raise AppError(
                "OpenRouter authentication failed",
                status_code=502,
                code="AI_PROVIDER_AUTHENTICATION_ERROR",
            )
        if response.status_code == 429:
            raise AppError(
                "OpenRouter rate limit exceeded",
                status_code=429,
                code="AI_PROVIDER_RATE_LIMIT",
            )
        if response.is_error:
            raise AppError(
                "OpenRouter returned an error",
                status_code=502,
                code="AI_PROVIDER_ERROR",
            )

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AppError(
                "OpenRouter returned a malformed response",
                status_code=502,
                code="AI_PROVIDER_RESPONSE_ERROR",
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise AppError(
                "OpenRouter returned an empty response",
                status_code=502,
                code="AI_PROVIDER_RESPONSE_ERROR",
            )

        response_model = payload.get("model", model)
        if not isinstance(response_model, str) or not response_model.strip():
            raise AppError(
                "OpenRouter returned a malformed response",
                status_code=502,
                code="AI_PROVIDER_RESPONSE_ERROR",
            )

        metadata: dict[str, Any] = {"provider": "openrouter"}
        if isinstance(payload.get("usage"), dict):
            metadata["usage"] = payload["usage"]
        return GenerationResult(
            answer=content,
            model_used=response_model,
            metadata=metadata,
        )


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def estimate_prompt_tokens(text: str) -> int:
    """Return a rough token estimate for development diagnostics only.

    Uses a 4-characters-per-token heuristic. This is intentionally NOT a
    tokenizer-equivalent count; it exists so the dev latency diagnostics can
    report a stable, non-zero ``final_context_token_count`` without an extra
    third-party dependency or API round trip.
    """
    if not isinstance(text, str) or not text.strip():
        return 0
    return max(1, (len(text) + 3) // 4)


def _build_user_content(context: AIContext) -> str:
    # NOTE: the task §13 token optimization ("no per-chunk metadata in the
    # generation prompt") is preserved: only chunk ids + raw text are sent.
    knowledge = "\n\n".join(
        "[Retrieved chunk {chunk_id}]\n{text}".format(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
        )
        for chunk in context.retrieved_knowledge
    )

    # Surface the interpreted intent only when a conversational rewrite
    # actually changed the wording of the question. This keeps retrieval
    # unambiguous for the model without ever replacing the user's own words.
    interpreted = ""
    if (
        context.retrieval_query
        and context.retrieval_query.strip() != context.user_question.strip()
    ):
        interpreted = f"\n\nInterpreted question:\n{context.retrieval_query.strip()}"

    conversation_history = ""
    if context.conversation_history:
        history_parts = []
        for turn in context.conversation_history:
            role = "User" if turn.role == "user" else "Assistant"
            history_parts.append(f"{role}: {turn.content}")
        conversation_history = "\n\nConversation history:\n" + "\n".join(history_parts) + "\n"

    return (
        f"Student question:\n{context.user_question}"
        f"{interpreted}\n\n"
        "Retrieved college knowledge:\n"
        f"{knowledge}"
        f"{conversation_history}"
    )