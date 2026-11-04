"""Fake SMTP only: no test in this feature can send real mail."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.config import settings
from app.services.email import smtp_transport
from app.services.email.contracts import InvitationEmail


@pytest.fixture(autouse=True)
def smtp_client(monkeypatch):
    client = Mock()
    client.connect = AsyncMock()
    client.login = AsyncMock()
    client.send_message = AsyncMock(return_value=({}, "accepted"))
    client.quit = AsyncMock()
    client.is_connected = True
    factory = Mock(return_value=client)
    monkeypatch.setattr(smtp_transport.aiosmtplib, "SMTP", factory)
    return client, factory


@pytest.fixture
def smtp_settings(monkeypatch):
    values = {
        "environment": "development", "email_allow_live_in_development": True,
        "email_provider": "smtp", "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "smtp_username": "sender@gmail.com", "smtp_password": "fake-app-password",
        "email_from": "CollegeAIChatbot <sender@gmail.com>", "email_reply_to": "",
        "email_base_url": "https://app.example.edu", "email_provider_api_key": "",
        "email_provider_max_retries": 0,
    }
    for key, value in values.items():
        monkeypatch.setattr(settings, key, value)
    return values


@pytest.fixture
def message():
    return InvitationEmail(
        to_email="student@example.com", subject="Set up your student account",
        body="Use your secure setup link.", html_body="<p>Use your secure setup link.</p>",
        institution_name="Example College", invitation_url="https://app.example.edu/student-setup#secret",
        expires_at=None, idempotency_key="student-onboarding:invitation:1",
    )
