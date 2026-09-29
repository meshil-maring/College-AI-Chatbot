import logging

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 6.15.7 — environments in which the DEV/TEST-only authentication
# helpers may be enabled. Anything else (production, prod, staging, a typo,
# an empty value, ...) is treated as NON-development and refuses the flag.
# ---------------------------------------------------------------------------
DEV_TEST_ENVIRONMENTS: frozenset[str] = frozenset(
    {"development", "dev", "local", "test", "testing"}
)


class Settings(BaseSettings):
    app_name: str = "College AI Chatbot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    # Comma-separated host names accepted by TrustedHostMiddleware. An empty
    # value uses loopback/test defaults locally and is rejected in production.
    allowed_hosts: str = ""
    # None means enabled locally and disabled in deployed environments.
    api_docs_enabled: bool | None = None

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""

    max_upload_size_mb: int = 50

    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "documents"

    ai_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_site_url: str = ""
    openrouter_app_name: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "qwen/qwen3-embedding-8b"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 100
    embedding_request_timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    # Phase 5.7b — bounded multi-turn conversational context.
    # Maximum number of persisted messages (user+assistant combined) included
    # in the generation context for an existing conversation.
    conversation_history_max_messages: int = 10

    # ------------------------------------------------------------------
    # Conversational RAG — query interpretation & retrieval budget.
    #
    # retrieval_top_k:
    #   Number of nearest knowledge chunks passed from the chat boundary to
    #   vector retrieval. Kept intentionally small so the generation prompt
    #   receives only the most relevant knowledge (section-sized chunks),
    #   instead of every near match in the scoped corpus.
    # rewrite_history_exchanges:
    #   Maximum number of complete user/assistant exchanges (2 messages per
    #   exchange) used to interpret a follow-up question before retrieval.
    # rewrite_max_history_chars:
    #   Hard character budget for the conversation excerpt sent to the
    #   query-interpretation step. The rewriter must stay token-cheap.
    # ------------------------------------------------------------------
    retrieval_top_k: int = Field(default=4, gt=0, le=20)
    # Public RAG context is independently bounded after repository-backed
    # provenance verification. Oversized chunks are excluded rather than
    # truncated so the application never changes their factual meaning.
    public_context_max_chunk_chars: int = Field(default=4000, gt=0)
    public_context_max_chars: int = Field(default=12000, gt=0)
    # Public generation controls are server-owned. They are deliberately not
    # represented in PublicChatRequest, so anonymous callers cannot select a
    # model, provider, output budget, or request duration.
    public_generation_max_tokens: int = Field(default=800, gt=0, le=4096)
    public_generation_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    public_response_max_chars: int = Field(default=12000, gt=0)
    # Phase 7.8 -- process-local public abuse/resource controls.  The request
    # schema retains its absolute 4,000-character contract; deployments may
    # lower (but never raise) the effective message ceiling.
    public_max_message_chars: int = Field(default=4000, gt=0, le=4000)
    public_max_body_bytes: int = Field(default=8192, ge=4096, le=1_048_576)
    public_body_read_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    public_rate_limit_enabled: bool = True
    public_rate_limit_requests: int = Field(default=60, gt=0)
    public_rate_limit_window_seconds: int = Field(default=60, gt=0, le=3600)
    public_institution_rate_limit_requests: int = Field(default=180, gt=0)
    public_global_rate_limit_requests: int = Field(default=600, gt=0)
    public_concurrency_limit: int = Field(default=8, gt=0, le=1000)
    public_institution_concurrency_limit: int = Field(default=4, gt=0, le=1000)
    public_overload_retry_after_seconds: int = Field(default=2, gt=0, le=60)
    rewrite_history_exchanges: int = 2
    rewrite_max_history_chars: int = 1000

    # ------------------------------------------------------------------
    # DEVELOPMENT / TESTING ONLY.
    #
    # Gates the dev-only password recovery/reset feature (see
    # app/api/dev_auth.py). Must be `False` (the default) everywhere except
    # a local development/testing environment. Never enable in production.
    # ------------------------------------------------------------------
    dev_test_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _dev_test_mode_requires_dev_environment(self) -> "Settings":
        """Fail closed when the dev-only authentication helpers are enabled
        outside a local development/testing environment (Phase 6.15.7).

        ``DEV_TEST_MODE=true`` exposes the development-only password
        recovery/reset endpoints (``app/api/dev_auth.py``) and the matching
        frontend UI. A misconfigured deployment must NOT silently ship those
        endpoints, so the application refuses to start instead of running in
        an unsafe state. The check is allowlist-based: only the explicit local
        values in ``DEV_TEST_ENVIRONMENTS`` permit the flag, so a typo (or a
        new environment name) can never enable it by accident.

        Constructing ``Settings`` directly (tests, scripts) is unaffected —
        the validator only inspects the two values that were resolved.
        """
        environment = (self.environment or "").strip().lower()
        if not self.dev_test_mode:
            return self
        if environment not in DEV_TEST_ENVIRONMENTS:
            raise ValueError(
                "DEV_TEST_MODE cannot be enabled outside a local "
                "development/testing environment. Set ENVIRONMENT to one of "
                f"{sorted(DEV_TEST_ENVIRONMENTS)} or set DEV_TEST_MODE=false. "
                "Refusing to start so that the development-only password "
                "recovery endpoints can never be exposed in a deployed "
                "environment."
            )
        logger.warning(
            "DEV_TEST_MODE is enabled (ENVIRONMENT=%s): development-only "
            "password recovery/reset endpoints are exposed. Never enable this "
            "outside local development/testing.",
            environment,
        )
        return self

    @model_validator(mode="after")
    def _validate_public_resource_controls(self) -> "Settings":
        if self.public_institution_concurrency_limit > self.public_concurrency_limit:
            raise ValueError(
                "PUBLIC_INSTITUTION_CONCURRENCY_LIMIT must not exceed "
                "PUBLIC_CONCURRENCY_LIMIT"
            )
        if self.public_max_body_bytes <= self.public_max_message_chars:
            raise ValueError(
                "PUBLIC_MAX_BODY_BYTES must leave room for the JSON request envelope"
            )
        return self

    @property
    def is_local_environment(self) -> bool:
        return (self.environment or "").strip().lower() in DEV_TEST_ENVIRONMENTS

    @property
    def effective_allowed_hosts(self) -> list[str]:
        configured = [
            host.strip()
            for host in (self.allowed_hosts or "").split(",")
            if host.strip()
        ]
        if configured:
            return configured
        if self.is_local_environment:
            return ["localhost", "127.0.0.1", "testserver"]
        return []

    @property
    def effective_api_docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.is_local_environment


settings = Settings()
