from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

from aiosmtplib import errors
import pytest

from app.config import settings
from app.services.email import email_delivery
from app.services.invitations import student_onboarding as onboarding
from app.services.invitations.student_onboarding_email import send_setup_link

TOKEN = "a" * 43
INVITATION_ID = "20000000-0000-0000-0000-000000000001"
TENANT_ID = "10000000-0000-0000-0000-000000000001"
SECTION_ID = "30000000-0000-0000-0000-000000000001"
EXPIRY = datetime(2099, 1, 1, tzinfo=timezone.utc)


def send():
    return send_setup_link(
        to_email="student@example.com", institution_name="Example College",
        student_name="Ada <script>", batch_code="B26", section_name="A",
        raw_token=TOKEN, expires_at=EXPIRY, invitation_id=INVITATION_ID, attempt=1,
    )


def test_student_setup_email_uses_smtp_and_existing_fragment_link(smtp_settings, smtp_client):
    result = send()
    assert result.status == "sent" and result.provider == "smtp"
    message = smtp_client[0].send_message.call_args.args[0]
    link = f"https://app.example.edu/student-setup#{TOKEN}"
    assert link in message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()
    assert link in html and "CollegeAIChatbot" in html
    assert "Ada &lt;script&gt;" in html and "<script>" not in html


def test_missing_credentials_return_failed_delivery(smtp_settings, monkeypatch, smtp_client):
    monkeypatch.setattr(settings, "smtp_password", "")
    result = send()
    assert result.status == "failed" and result.detail == "DELIVERY_CONFIGURATION_ERROR"
    smtp_client[1].assert_not_called()


def test_capture_mode_keeps_smtp_offline(smtp_settings, monkeypatch, smtp_client):
    monkeypatch.setattr(settings, "environment", "test")
    email_delivery.reset_email_outbox()
    try:
        assert send().provider == "test"
        assert len(email_delivery.captured_emails()) == 1
        smtp_client[1].assert_not_called()
    finally:
        email_delivery.reset_email_outbox()


@pytest.mark.parametrize("failed", [False, True])
def test_invitation_workflow_records_smtp_outcome(smtp_settings, smtp_client, monkeypatch, failed):
    if failed:
        smtp_client[0].login.side_effect = errors.SMTPAuthenticationError(535, "denied")
    record = Mock(return_value=True)
    monkeypatch.setattr(onboarding.repository, "record_delivery", record)
    client = Mock()
    row = {
        "invitation_id": INVITATION_ID, "institution_id": TENANT_ID,
        "academic_section_id": SECTION_ID, "student_name": "Ada",
        "email": "student@example.com", "register_number": "REG-1",
        "university_roll_number": None, "token_hash": "b" * 64,
        "expires_at": EXPIRY, "created_at": datetime.now(timezone.utc),
        "status": "pending", "email_delivery_status": "pending",
        "email_delivery_attempts": 0,
    }
    result = onboarding.deliver_setup_link(
        client, UUID(TENANT_ID), "actor", row, TOKEN, EXPIRY,
    )
    expected = "failed" if failed else "sent"
    assert result.delivery_status == expected
    assert record.call_args.kwargs["status"] == expected
    if not failed:
        assert "Inbox delivery is not confirmed" in result.delivery_message


class _CapturedTable:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def update(self, values: dict[str, object]):
        self.values.update(values)
        return self

    def eq(self, column: str, value: object):
        assert column == "invitation_id"
        return self

    def execute(self):
        return type("Response", (), {"data": [True]})()


def test_failed_delivery_refunds_resend_window_count(smtp_settings, smtp_client, monkeypatch):
    smtp_client[0].login.side_effect = errors.SMTPAuthenticationError(535, "denied")
    table = _CapturedTable()
    client = Mock()
    client.table = lambda name: table
    record = Mock(return_value=True)
    monkeypatch.setattr(onboarding.repository, "record_delivery", record)
    row = {
        "invitation_id": INVITATION_ID, "institution_id": TENANT_ID,
        "academic_section_id": SECTION_ID, "student_name": "Ada",
        "email": "student@example.com", "register_number": "REG-1",
        "university_roll_number": None, "token_hash": "b" * 64,
        "expires_at": EXPIRY, "created_at": datetime.now(timezone.utc),
        "status": "pending", "email_delivery_status": "pending",
        "email_delivery_attempts": 0, "resend_window_count": 3,
    }
    result = onboarding.deliver_setup_link(
        client, UUID(TENANT_ID), "actor", row, TOKEN, EXPIRY,
    )
    assert result.delivery_status == "failed"
    # The undelivered attempt must not consume a resend: refund back to 2.
    assert table.values["resend_window_count"] == 2
    assert row["resend_window_count"] == 2
