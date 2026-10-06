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
    # Comma-separated browser origins. Empty intentionally means same-origin
    # only (no CORS middleware). Wildcards are never accepted in deployments.
    cors_allowed_origins: str = ""
    # None means enabled locally and disabled in deployed environments.
    api_docs_enabled: bool | None = None

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""
    # Optional explicit issuer. Supabase's canonical issuer is derived from
    # SUPABASE_URL when this is empty.
    supabase_jwt_issuer: str = ""
    jwt_jwks_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    max_bearer_token_chars: int = Field(default=8192, ge=1024, le=32768)

    max_upload_size_mb: int = 50
    max_request_body_bytes: int = Field(default=1_048_576, ge=4096, le=16_777_216)
    webhook_max_body_bytes: int = Field(default=262_144, ge=4096, le=1_048_576)
    upload_request_overhead_bytes: int = Field(
        default=1_048_576, ge=65_536, le=8_388_608
    )
    request_body_read_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_csv_upload_bytes: int = Field(default=5_242_880, ge=1024, le=16_777_216)
    max_csv_rows: int = Field(default=5000, gt=0, le=50_000)
    max_document_pages: int = Field(default=500, gt=0, le=5000)
    max_extracted_text_chars: int = Field(default=2_000_000, gt=1000, le=20_000_000)
    max_docx_archive_entries: int = Field(default=2000, gt=0, le=10_000)
    max_docx_uncompressed_bytes: int = Field(
        default=100_000_000, gt=1_000_000, le=500_000_000
    )
    max_docx_compression_ratio: int = Field(default=100, ge=2, le=1000)

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
    # Coarse API-wide defense in depth. These counters are process-local; the
    # production edge must enforce shared limits across workers/instances.
    api_rate_limit_enabled: bool = True
    api_rate_limit_window_seconds: int = Field(default=60, gt=0, le=3600)
    api_client_rate_limit_requests: int = Field(default=2000, gt=0)
    api_global_rate_limit_requests: int = Field(default=10_000, gt=0)
    authenticated_ai_rate_limit_requests: int = Field(default=120, gt=0)
    # ------------------------------------------------------------------
    # Phase 7.15 -- invitation email delivery boundary.
    #
    # `email_provider` selects the delivery implementation through the
    # `EmailDeliveryProvider` abstraction. "local" (the default) captures
    # messages in a process-local outbox and NEVER contacts an external
    # service. Any other value names a production provider whose vendor
    # integration is a later phase; the configuration boundary exists now so
    # no provider is hard-coded.
    #
    # `email_provider_api_key` is a server-side secret: it is never returned
    # through any API, never logged and never included in a frontend bundle
    # (the frontend reads only `VITE_*` variables).
    #
    # `email_base_url` is the AUTHORITATIVE origin for invitation links. A
    # production URL is therefore never built from an untrusted request Host
    # header.
    # ------------------------------------------------------------------
    email_provider: str = "local"
    email_from: str = "no-reply@localhost"
    email_reply_to: str = ""
    email_base_url: str = "http://localhost:5173"
    email_provider_api_key: str = ""
    # Passed to the vendor adapter on every request. Retries are additional to
    # the first call and remain bounded; delays use capped exponential backoff.
    email_provider_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    email_provider_max_retries: int = Field(default=2, ge=0, le=5)
    email_provider_retry_base_seconds: float = Field(default=0.25, ge=0, le=10)
    email_provider_retry_cap_seconds: float = Field(default=2.0, ge=0, le=60)
    # Phase 7.17 durable outbox. The encryption key protects the one-time
    # delivery secret at rest; deployments must provide a Fernet key. Local
    # and test environments use an explicitly non-production deterministic
    # key so automated tests can never depend on a real secret manager.
    email_outbox_token_encryption_key: str = ""
    email_worker_batch_size: int = Field(default=20, gt=0, le=200)
    email_worker_lock_seconds: int = Field(default=120, ge=30, le=3600)
    email_outbox_retry_limit: int = Field(default=3, gt=0, le=20)
    # Phase 7.18 -- Mailgun is the only authorized production transport.
    # These values are backend-only. `mailgun_base_url` supports Mailgun's US
    # and EU API origins without baking a region into application code.
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    mailgun_base_url: str = "https://api.mailgun.net"
    mailgun_webhook_signing_key: str = ""
    mailgun_webhook_tolerance_seconds: int = Field(default=900, ge=30, le=3600)

    # ------------------------------------------------------------------
    # Phase 7.15 -- invitation abuse controls.
    #
    # Reuses the Phase 7.8 process-local sliding-window primitive, but with
    # SEPARATE budgets because invitation traffic has different
    # characteristics from public chat: a legitimate invitee performs a
    # handful of operations, so the per-token acceptance budget is tight
    # while the per-IP inspection budget stays generous enough for one
    # confused person reloading a link a few times.
    # ------------------------------------------------------------------
    invitation_rate_limit_enabled: bool = True
    invitation_rate_limit_window_seconds: int = Field(default=300, gt=0, le=3600)
    invitation_inspect_ip_limit_requests: int = Field(default=60, gt=0)
    invitation_accept_token_limit_requests: int = Field(default=5, gt=0)
    invitation_accept_ip_limit_requests: int = Field(default=20, gt=0)
    invitation_resend_invitation_limit_requests: int = Field(default=3, gt=0)
    invitation_resend_actor_limit_requests: int = Field(default=20, gt=0)
    invitation_resend_institution_limit_requests: int = Field(default=10, gt=0)
    invitation_resend_ip_limit_requests: int = Field(default=5, gt=0)
    invitation_retry_after_cap_seconds: int = Field(default=60, gt=0, le=600)

    # Authentication endpoints are high-value, low-volume operations. These
    # process-local limits complement (but do not replace) edge-level limits.
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_window_seconds: int = Field(default=300, gt=0, le=3600)
    auth_login_ip_limit_requests: int = Field(default=30, gt=0)
    auth_registration_ip_limit_requests: int = Field(default=10, gt=0)
    auth_recovery_ip_limit_requests: int = Field(default=5, gt=0)
    auth_password_ip_limit_requests: int = Field(default=10, gt=0)
    auth_recovery_redirect_url: str = ""

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
        if self.email_provider_retry_base_seconds > self.email_provider_retry_cap_seconds:
            raise ValueError(
                "EMAIL_PROVIDER_RETRY_BASE_SECONDS must not exceed "
                "EMAIL_PROVIDER_RETRY_CAP_SECONDS"
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
    def effective_cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in (self.cors_allowed_origins or "").split(",")
            if origin.strip()
        ]

    @property
    def effective_supabase_jwt_issuer(self) -> str:
        configured = (self.supabase_jwt_issuer or "").strip().rstrip("/")
        if configured:
            return configured
        return f"{self.supabase_url.strip().rstrip('/')}/auth/v1"

    @property
    def max_upload_request_body_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024 + self.upload_request_overhead_bytes

    @property
    def effective_api_docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.is_local_environment

    @property
    def effective_auth_recovery_redirect_url(self) -> str:
        configured = self.auth_recovery_redirect_url.strip()
        if configured:
            return configured
        if self.is_local_environment:
            return f"{self.email_base_url.rstrip('/')}/reset-password"
        raise ValueError("AUTH_RECOVERY_REDIRECT_URL must be configured outside local environments")


settings = Settings()
