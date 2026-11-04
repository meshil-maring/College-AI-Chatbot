import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.core.startup_validation.email import collect_email_checks
from app.services.email import email_delivery as delivery


def test_smtp_is_configured_without_mailgun_or_provider_api_key(smtp_settings):
    provider = delivery.get_email_provider()
    assert provider.is_configured
    assert provider.name == "smtp"
    assert provider.health().state == delivery.ProviderHealthState.CONFIGURED


@pytest.mark.parametrize("field,value,label", [
    ("smtp_host", "", "SMTP_HOST"),
    ("smtp_host", "smtp.gmail.com/path", "SMTP_HOST"),
    ("smtp_username", "", "SMTP_USERNAME"),
    ("smtp_password", "", "SMTP_PASSWORD"),
    ("smtp_port", 465, "SMTP_PORT"),
    ("email_from", "bad-address", "EMAIL_FROM"),
    ("email_reply_to", "bad-address", "EMAIL_REPLY_TO"),
    ("email_base_url", "https://[", "EMAIL_BASE_URL"),
])
def test_incomplete_smtp_fails_safely(smtp_settings, monkeypatch, field, value, label):
    monkeypatch.setattr(settings, field, value)
    with pytest.raises(delivery.EmailDeliveryError) as error:
        delivery.get_email_provider()
    assert error.value.code == delivery.DELIVERY_CONFIGURATION_ERROR
    assert label in str(error.value)
    assert "fake-app-password" not in str(error.value)


@pytest.mark.parametrize("environment", ["test", "testing", "development"])
def test_capture_environment_never_connects(smtp_settings, monkeypatch, smtp_client, environment):
    monkeypatch.setattr(settings, "environment", environment)
    if environment == "development":
        monkeypatch.setattr(settings, "email_allow_live_in_development", False)
    provider = delivery.get_email_provider()
    assert isinstance(provider, delivery.LocalEmailProvider)
    smtp_client[1].assert_not_called()


def test_deployed_smtp_checks_do_not_require_mailgun(smtp_settings):
    cfg = Settings(
        _env_file=None, **{**smtp_settings, "environment": "production", "debug": False},
        email_outbox_token_encryption_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    )
    checks = collect_email_checks(cfg, is_local=False)
    assert checks and all(check.ok for check in checks)
    assert not any(check.name.startswith("MAILGUN") for check in checks)
    assert "fake-app-password" not in repr(cfg)


def test_startup_and_service_share_missing_configuration_rules(smtp_settings):
    cfg = Settings(_env_file=None, **{**smtp_settings, "smtp_password": ""})
    checks = collect_email_checks(cfg, is_local=True)
    assert any(check.name == "SMTP_PASSWORD" and not check.ok for check in checks)


@pytest.mark.parametrize("port", [0, 65536])
def test_port_bounds_are_validated(port):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, smtp_port=port)
