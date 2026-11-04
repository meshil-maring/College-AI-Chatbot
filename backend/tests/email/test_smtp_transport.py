from dataclasses import replace
import logging

from aiosmtplib import errors
import pytest

from app.config import settings
from app.services.email import email_delivery as delivery


def test_submission_uses_starttls_auth_html_and_text(smtp_settings, smtp_client, message):
    client, factory = smtp_client
    result = delivery.get_email_provider().send_invitation(message)
    assert result.status == "sent" and result.provider == "smtp"
    assert result.provider_message_id
    options = factory.call_args.kwargs
    assert options["hostname"] == "smtp.gmail.com" and options["port"] == 587
    assert options["start_tls"] is True and options["use_tls"] is False
    assert options["validate_certs"] is True
    client.login.assert_awaited_once_with("sender@gmail.com", "fake-app-password")
    sent = client.send_message.call_args.args[0]
    assert sent.get_body(preferencelist=("plain",)).get_content().strip() == message.body
    assert sent.get_body(preferencelist=("html",)).get_content().strip() == message.html_body
    assert message.idempotency_key not in sent.as_string()
    assert client.send_message.call_args.kwargs["recipients"] == [message.to_email]
    client.quit.assert_awaited_once()
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_provider_submits_without_blocking_the_calling_loop(smtp_settings, message):
    result = await delivery.get_email_provider().send_invitation_async(message)
    assert result.status == "sent" and result.provider == "smtp"


@pytest.mark.parametrize("address", ["bad", "student@example.com\r\nBcc: attacker@example.com", "a@example.com,b@example.com"])
def test_invalid_recipient_is_rejected_before_connection(smtp_settings, smtp_client, message, address):
    with pytest.raises(delivery.EmailDeliveryError) as error:
        delivery.get_email_provider().send_invitation(replace(message, to_email=address))
    assert error.value.code == delivery.DELIVERY_PERMANENT_FAILURE
    smtp_client[1].assert_not_called()


def test_subject_header_injection_is_rejected(smtp_settings, smtp_client, message):
    with pytest.raises(delivery.EmailDeliveryError):
        delivery.get_email_provider().send_invitation(replace(message, subject="Hello\nBcc: evil@example.com"))
    smtp_client[1].assert_not_called()


@pytest.mark.parametrize("stage,error,code,retryable", [
    ("login", errors.SMTPAuthenticationError(535, "secret provider diagnostic"), "DELIVERY_CONFIGURATION_ERROR", False),
    ("connect", OSError("secret host diagnostic"), "DELIVERY_TEMPORARY_FAILURE", True),
    ("connect", errors.SMTPTimeoutError("timed out"), "DELIVERY_TIMEOUT", True),
    ("connect", errors.SMTPNotSupported("STARTTLS required"), "DELIVERY_CONFIGURATION_ERROR", False),
    ("send_message", errors.SMTPDataError(451, "try later"), "DELIVERY_TEMPORARY_FAILURE", True),
    ("send_message", errors.SMTPDataError(550, "rejected"), "DELIVERY_PERMANENT_FAILURE", False),
    ("send_message", errors.SMTPTimeoutError("lost acknowledgement"), "DELIVERY_TIMEOUT", False),
    ("send_message", errors.SMTPServerDisconnected("lost acknowledgement"), "DELIVERY_TEMPORARY_FAILURE", False),
])
def test_failure_categories_and_cleanup(smtp_settings, smtp_client, message, stage, error, code, retryable):
    client, _ = smtp_client
    getattr(client, stage).side_effect = error
    with pytest.raises(delivery.EmailDeliveryError) as caught:
        delivery.get_email_provider().send_invitation(message)
    assert caught.value.code == code and caught.value.retryable is retryable
    assert "secret" not in str(caught.value)
    client.close.assert_called_once()


@pytest.mark.parametrize("code,temporary", [(450, True), (550, False)])
def test_refused_recipient_is_not_a_success(smtp_settings, smtp_client, message, code, temporary):
    smtp_client[0].send_message.side_effect = errors.SMTPRecipientsRefused([
        errors.SMTPRecipientRefused(code, "provider diagnostic", message.to_email),
    ])
    with pytest.raises(delivery.EmailDeliveryError) as caught:
        delivery.get_email_provider().send_invitation(message)
    assert caught.value.retryable is temporary


def test_quit_failure_does_not_retry_an_accepted_message(smtp_settings, smtp_client, message):
    smtp_client[0].quit.side_effect = errors.SMTPServerDisconnected("disconnect")
    assert delivery.get_email_provider().send_invitation(message).status == "sent"
    smtp_client[0].send_message.assert_awaited_once()
    smtp_client[0].close.assert_called_once()


def test_uncertain_submission_ignores_automatic_retry_budget(smtp_settings, smtp_client, message, monkeypatch):
    monkeypatch.setattr(settings, "email_provider_max_retries", 2)
    smtp_client[0].send_message.side_effect = errors.SMTPTimeoutError("lost acknowledgement")
    with pytest.raises(delivery.EmailDeliveryError):
        delivery.get_email_provider().send_invitation(message)
    smtp_client[0].send_message.assert_awaited_once()


def test_explicit_temporary_rejection_can_retry(smtp_settings, smtp_client, message, monkeypatch):
    monkeypatch.setattr(settings, "email_provider_max_retries", 1)
    monkeypatch.setattr(settings, "email_provider_retry_base_seconds", 0)
    smtp_client[0].send_message.side_effect = [
        errors.SMTPDataError(451, "try later"), ({}, "accepted"),
    ]
    assert delivery.get_email_provider().send_invitation(message).status == "sent"
    assert smtp_client[0].send_message.await_count == 2


def test_logs_exclude_message_recipient_token_and_password(smtp_settings, message, caplog):
    with caplog.at_level(logging.INFO):
        delivery.get_email_provider().send_invitation(message)
    assert "email_smtp_submitted" in caplog.text
    for private in ("fake-app-password", message.to_email, message.invitation_url, message.body):
        assert private not in caplog.text
