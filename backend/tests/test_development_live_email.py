import httpx
import pytest

from app.config import settings
from app.services import email_delivery as delivery


@pytest.fixture
def sandbox(monkeypatch):
    for key, value in {
        'environment': 'development', 'email_allow_live_in_development': True,
        'email_provider': 'mailgun', 'mailgun_api_key': 'fake-private-key',
        'mailgun_domain': 'sandbox123.mailgun.org',
        'mailgun_base_url': 'https://api.mailgun.net',
        'email_from': 'noreply@sandbox123.mailgun.org',
        'email_base_url': 'http://localhost:5173',
    }.items():
        monkeypatch.setattr(settings, key, value)


def test_real_sandbox_test_selects_mailgun_only_after_opt_in(sandbox, monkeypatch):
    provider = delivery.get_email_provider()
    assert isinstance(provider, delivery.ProductionEmailProvider)
    assert provider.is_configured
    monkeypatch.setattr(settings, 'email_allow_live_in_development', False)
    assert type(delivery.get_email_provider()) is delivery.LocalEmailProvider


@pytest.mark.parametrize('environment', ['test', 'testing'])
def test_test_environments_still_capture_with_live_setting_enabled(sandbox, monkeypatch, environment):
    monkeypatch.setattr(settings, 'environment', environment)
    assert type(delivery.get_email_provider()) is delivery.TestEmailProvider


@pytest.mark.parametrize('key,value,label', [
    ('mailgun_api_key', '', 'MAILGUN_API_KEY'),
    ('mailgun_domain', '', 'MAILGUN_DOMAIN'),
    ('email_provider', 'local', 'EMAIL_PROVIDER'),
    ('email_from', 'noreply@yourcollege.edu', 'EMAIL_FROM using the sandbox domain'),
    ('email_from', 'not-an-email', 'EMAIL_FROM'),
    ('mailgun_base_url', 'https://wrong.example', 'MAILGUN_BASE_URL'),
    ('email_base_url', 'javascript:invalid', 'EMAIL_BASE_URL'),
])
def test_incomplete_live_configuration_does_not_fall_back_to_capture_or_expose_secrets(sandbox, monkeypatch, key, value, label):
    monkeypatch.setattr(settings, key, value)
    with pytest.raises(delivery.EmailDeliveryError) as error:
        delivery.get_email_provider()
    assert label in str(error.value)
    assert 'fake-private-key' not in str(error.value)


def test_opted_in_student_message_reaches_mailgun_transport_without_real_network(sandbox, monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={'id': '<test-message>'})
    transport = delivery.MailgunEmailTransport(api_key='fake-private-key', domain=settings.mailgun_domain,
        base_url=settings.mailgun_base_url, client=httpx.Client(transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(delivery, '_build_production_transport', lambda *_: transport)
    provider = delivery.get_email_provider()
    result = provider.send_invitation(delivery.InvitationEmail(to_email='verified@college.edu',
        subject='Complete student registration', body='Register using the provided link.',
        institution_name='College', invitation_url='http://localhost:5173/login/student?register=1',
        expires_at=None, idempotency_key='student-registration:test'))
    assert result.provider == 'mailgun' and result.status == 'sent'
    assert len(requests) == 1 and str(requests[0].url) == 'https://api.mailgun.net/v3/sandbox123.mailgun.org/messages'
