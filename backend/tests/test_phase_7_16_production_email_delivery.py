"""Phase 7.16 provider-neutral production email reliability contracts.

No test performs network I/O or sends real email. Fake transports exercise the
boundary that a future explicitly selected vendor adapter must implement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from app.config import Settings, settings
from app.core.startup_validation import run_startup_configuration_validation
from app.services import email_delivery as delivery

RAW_TOKEN = "phase-7-16-raw-secret-token"


@pytest.fixture(autouse=True)
def _provider_secret(monkeypatch):
    monkeypatch.setattr(settings, "email_provider_api_key", "fake-provider-key")
    monkeypatch.setattr(settings, "email_base_url", "https://app.example.edu")


def _message() -> delivery.InvitationEmail:
    return delivery.build_invitation_email(
        to_email="admin@example.edu",
        institution_name="Example University",
        raw_token=RAW_TOKEN,
        expires_at="2099-01-01T00:00:00+00:00",
        idempotency_key=delivery.build_delivery_idempotency_key("invite-123", 2),
    )


@dataclass
class _Transport:
    outcomes: list[object]

    def __post_init__(self):
        self.calls: list[dict[str, object]] = []

    def send_invitation(self, email, **kwargs):
        self.calls.append({"email": email, **kwargs})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _provider(transport, **kwargs) -> delivery.ProductionEmailProvider:
    return delivery.ProductionEmailProvider(
        provider_name="authorized-provider-placeholder",
        from_address="no-reply@example.edu",
        reply_to="support@example.edu",
        transport=transport,
        timeout_seconds=7.5,
        max_retries=kwargs.pop("max_retries", 2),
        retry_base_seconds=0,
        retry_cap_seconds=kwargs.pop("retry_cap_seconds", 2),
        sleep=kwargs.pop("sleep", lambda _: None),
        **kwargs,
    )


def test_environment_selection_is_explicit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_provider", "some-vendor")
    monkeypatch.setattr(settings, "environment", "local")
    assert type(delivery.get_email_provider()) is delivery.LocalEmailProvider

    monkeypatch.setattr(settings, "environment", "test")
    assert type(delivery.get_email_provider()) is delivery.TestEmailProvider

    monkeypatch.setattr(settings, "environment", "production")
    assert isinstance(delivery.get_email_provider(), delivery.ProductionEmailProvider)


def test_production_never_falls_back_to_capture(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "local")
    assert isinstance(delivery.get_email_provider(), delivery.ProductionEmailProvider)


def test_production_startup_requires_email_configuration() -> None:
    cfg = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        allowed_hosts="api.example.edu",
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="public-placeholder",
        supabase_secret_key="secret-placeholder",
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
        openrouter_api_key="ai-placeholder",
        r2_endpoint_url="https://r2.example.edu",
        r2_access_key_id="r2-id-placeholder",
        r2_secret_access_key="r2-secret-placeholder",
        email_provider="local",
        email_provider_api_key="",
        email_base_url="http://localhost:5173",
    )
    with pytest.raises(RuntimeError) as error:
        run_startup_configuration_validation(cfg)
    message = str(error.value)
    assert "EMAIL_PROVIDER" in message
    assert "must be set to the authorized mailgun provider" in message
    assert "EMAIL_BASE_URL" in message
    assert "secret-placeholder" not in message


def test_success_passes_timeout_and_idempotency_without_token() -> None:
    transport = _Transport([delivery.ProviderSendResult("provider-message-1")])
    result = _provider(transport).send_invitation(_message())
    assert result.status == delivery.DELIVERY_SENT
    assert transport.calls[0]["timeout_seconds"] == 7.5
    key = str(transport.calls[0]["idempotency_key"])
    assert key == "admin-invitation:invite-123:2"
    assert RAW_TOKEN not in key


def test_timeout_retries_are_bounded_and_keep_one_idempotency_key() -> None:
    transport = _Transport([TimeoutError(), TimeoutError(), TimeoutError()])
    with pytest.raises(delivery.EmailDeliveryError) as error:
        _provider(transport).send_invitation(_message())
    assert error.value.code == delivery.DELIVERY_TIMEOUT
    assert len(transport.calls) == 3
    assert len({call["idempotency_key"] for call in transport.calls}) == 1


def test_temporary_failure_can_recover_within_retry_budget() -> None:
    transport = _Transport(
        [OSError("temporary"), delivery.ProviderSendResult("provider-message-2")]
    )
    result = _provider(transport).send_invitation(_message())
    assert result.status == delivery.DELIVERY_SENT
    assert len(transport.calls) == 2


def test_permanent_failure_is_never_retried() -> None:
    transport = _Transport(
        [
            delivery.EmailDeliveryError(
                "safe failure", code=delivery.DELIVERY_PERMANENT_FAILURE
            )
        ]
    )
    with pytest.raises(delivery.EmailDeliveryError) as error:
        _provider(transport).send_invitation(_message())
    assert error.value.code == delivery.DELIVERY_PERMANENT_FAILURE
    assert len(transport.calls) == 1


def test_rate_limit_honors_capped_retry_after() -> None:
    sleeps: list[float] = []
    transport = _Transport(
        [
            delivery.EmailDeliveryError(
                "safe rate limit",
                code=delivery.DELIVERY_RATE_LIMITED,
                retryable=True,
                retry_after_seconds=30,
            ),
            delivery.ProviderSendResult("provider-message-3"),
        ]
    )
    result = _provider(transport, retry_cap_seconds=2, sleep=sleeps.append).send_invitation(
        _message()
    )
    assert result.status == delivery.DELIVERY_SENT
    assert sleeps == [2]


def test_malformed_provider_response_is_permanent() -> None:
    transport = _Transport([object()])
    with pytest.raises(delivery.EmailDeliveryError) as error:
        _provider(transport).send_invitation(_message())
    assert error.value.code == delivery.DELIVERY_MALFORMED_RESPONSE
    assert len(transport.calls) == 1


def test_provider_specific_error_code_is_sanitized() -> None:
    class VendorProvider:
        name = "vendor"

        def send_invitation(self, email):
            raise delivery.EmailDeliveryError(
                "vendor diagnostic", code="VENDOR_ACCOUNT_123_REJECTED"
            )

    result = delivery.deliver_invitation_email(
        VendorProvider(),
        to_email="admin@example.edu",
        institution_name="Example University",
        raw_token=RAW_TOKEN,
        expires_at="2099-01-01T00:00:00+00:00",
        invitation_id="invite-123",
        delivery_attempt=1,
    )
    assert result.detail == delivery.DELIVERY_PERMANENT_FAILURE
    assert "VENDOR" not in str(result)


def test_unselected_vendor_reports_not_configured_health(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "not-selected")
    provider = delivery.get_email_provider()
    assert isinstance(provider, delivery.ProductionEmailProvider)
    assert provider.health().state == delivery.ProviderHealthState.NOT_CONFIGURED


def test_logs_never_leak_url_token_hash_password_or_provider_key(caplog) -> None:
    token_hash = "f" * 64
    password = "DoNotLogThisPassword!"
    transport = _Transport([TimeoutError(), TimeoutError(), TimeoutError()])
    with caplog.at_level(logging.INFO, logger="app.services.email_delivery"):
        result = delivery.deliver_invitation_email(
            _provider(transport),
            to_email="admin@example.edu",
            institution_name="Example University",
            raw_token=RAW_TOKEN,
            expires_at="2099-01-01T00:00:00+00:00",
            invitation_id="invite-123",
            delivery_attempt=1,
        )
    assert result.detail == delivery.DELIVERY_TIMEOUT
    for secret in (
        RAW_TOKEN,
        token_hash,
        password,
        "fake-provider-key",
        f"/admin-invite/{RAW_TOKEN}",
        "admin@example.edu",
    ):
        assert secret not in caplog.text
