"""Backend-only email transport, retry and outbox configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class EmailSettings(BaseSettings):
    # ------------------------------------------------------------------
    # Shared invitation email delivery boundary.
    #
    # `email_provider` selects the delivery implementation through the
    # `EmailDeliveryProvider` abstraction. "local" (the default) captures
    # messages in a process-local outbox and NEVER contacts an external
    # service. SMTP and Mailgun share the same workflow-facing contracts.
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
    # Explicit opt-in for real inbox tests without changing the app environment.
    # Test/testing environments always capture, even when this flag is true.
    email_allow_live_in_development: bool = False
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
    # STARTTLS is mandatory for SMTP; credentials never leave the backend.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = Field(default="", repr=False)
    # Retained Mailgun transport. `mailgun_base_url` supports Mailgun's US
    # and EU API origins without baking a region into application code.
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    mailgun_base_url: str = "https://api.mailgun.net"
    mailgun_webhook_signing_key: str = ""
    mailgun_webhook_tolerance_seconds: int = Field(default=900, ge=30, le=3600)
