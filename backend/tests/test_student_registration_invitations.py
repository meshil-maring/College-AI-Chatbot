from types import SimpleNamespace
from html import escape
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.students.student_registrations import StudentRegistrationCreate
from app.services.email import email_delivery
from app.services.invitations import student_registration_invitations as service
from app.services.students import student_registrations
from tests.test_student_class_registrations import Database, Query, SCOPE, TENANT, SECTION, USER, BATCH, stored, principal

REGISTRATION = '88888888-8888-4888-8888-888888888888'


class MailDatabase(Database):
    def __init__(self):
        super().__init__()
        self.deliveries, self.rpc_calls = {}, []

    def table(self, name):
        class MailQuery(Query):
            def execute(query):
                result = super().execute()
                if query.inserted is not None: result.data[0]['registration_id'] = REGISTRATION
                return result
        return MailQuery(self, name)

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        if name == 'claim_student_registration_invitation':
            status = self.deliveries.get(params['p_registration_id'], 'failed')
            claimed = status not in {'sent', 'sending'}
            if claimed: self.deliveries[params['p_registration_id']] = 'sending'
            return SimpleNamespace(execute=lambda: SimpleNamespace(data={'claimed': claimed, 'status': status, 'attempt_id': 'attempt-1'}))
        assert name == 'complete_student_registration_invitation'
        self.deliveries[params['p_registration_id']] = params['p_status']
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=True))


@pytest.fixture
def mail(monkeypatch):
    db = MailDatabase()
    db.tables['student_registrations'] = [stored(registration_id=REGISTRATION, email='ada@college.edu')]
    db.tables['institutions'] = [{'institution_id': TENANT, 'name': 'Test College', 'code': 'COLLEGE 1', 'is_active': True}]
    db.tables['academic_batches'] = [{'batch_id': BATCH, 'institution_id': TENANT, 'program_id': SCOPE['program_id'], 'start_year': 2026, 'end_year': 2030, 'is_active': True}]
    for module in (service, student_registrations):
        monkeypatch.setattr(module, 'get_admin_client', lambda: db)
        monkeypatch.setattr(module, '_assert_assigned', lambda *_args: SCOPE)
    monkeypatch.setattr(service.settings, 'email_base_url', 'https://college.example/app')
    messages = []
    provider = SimpleNamespace(name='mailgun')
    def send(message):
        messages.append(message)
        return email_delivery.EmailDeliveryResult('sent', provider.name)
    provider.send_invitation = send
    monkeypatch.setattr(email_delivery, 'get_email_provider', lambda: provider)
    return db, provider, messages


def test_send_uses_saved_recipient_trusted_signup_url_and_persistent_duplicate_guard(mail):
    db, _, messages = mail
    result = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert result['status'] == 'sent' and len(messages) == 1
    assert messages[0].to_email == 'ada@college.edu'
    assert messages[0].invitation_url == 'https://college.example/app/login/student?institution=COLLEGE+1&register=1'
    assert 'institution will review your account' in messages[0].body
    assert 'student-registration:' + REGISTRATION == messages[0].idempotency_key
    assert 'token' not in messages[0].invitation_url
    assert f'href="{escape(messages[0].invitation_url, quote=True)}"' in messages[0].html_body
    assert '>Complete registration</a>' in messages[0].html_body
    assert service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))['status'] == 'already_sent'
    assert len(messages) == 1 and not db.writes


def test_email_html_escapes_saved_student_and_institution_names(mail):
    db, _, messages = mail
    db.tables['student_registrations'][0]['student_name'] = '<script>alert("student")</script>'
    db.tables['institutions'][0]['name'] = '<img src=x onerror=alert("college")>'
    service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    html = messages[0].html_body
    assert '<script>' not in html and '<img' not in html
    assert '&lt;script&gt;' in html and '&lt;img' in html
    assert messages[0].invitation_url in messages[0].body


@pytest.mark.parametrize(('base', 'local'), [
    ('http://localhost:5173', True), ('http://127.0.0.1:5173', True),
    ('http://[::1]:5173', True), ('https://college.example', False),
])
def test_local_invitation_explains_how_to_open_the_link(mail, monkeypatch, base, local):
    _, _, messages = mail
    monkeypatch.setattr(service.settings, 'email_base_url', base)
    service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    for content in (messages[0].body, messages[0].html_body):
        assert ('computer running CollegeAI' in content) == local
        assert ('private browser window' in content) == local


@pytest.mark.parametrize('change', [{'institution_id': USER}, {'program_id': USER}, {'semester_id': USER}, {'section_code': 'B'}])
def test_foreign_or_out_of_scope_registration_cannot_send_mail(mail, change):
    db, _, messages = mail
    db.tables['student_registrations'][0].update(change)
    with pytest.raises(AppError) as error:
        service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert error.value.status_code == 404
    assert not messages and not db.rpc_calls


def test_revoked_permission_and_in_progress_delivery_never_send_duplicate_mail(mail, monkeypatch):
    db, _, messages = mail
    db.deliveries[REGISTRATION] = 'sending'
    assert service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))['status'] == 'pending'
    assert not messages
    def denied(*_args): raise AppError('Access revoked', 403, 'FORBIDDEN')
    monkeypatch.setattr(service, '_assert_assigned', denied)
    with pytest.raises(AppError): service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert not messages


def test_provider_failure_is_safe_and_retry_does_not_register_again(mail, caplog):
    db, provider, messages = mail
    original = provider.send_invitation
    def fail(_): raise RuntimeError('private provider secret')
    provider.send_invitation = fail
    result = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert result['status'] == 'failed' and 'secret' not in str(result)
    assert 'UNEXPECTED_ERROR' in caplog.text and 'private provider secret' not in caplog.text
    provider.send_invitation = original
    assert service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))['status'] == 'sent'
    assert len(messages) == 1 and not db.writes


@pytest.mark.parametrize(('code', 'http_status', 'guidance'), [
    (email_delivery.DELIVERY_CONFIGURATION_ERROR, 401, 'sending API key, domain and region'),
    (email_delivery.DELIVERY_CONFIGURATION_ERROR, 403, 'sending key permissions and domain'),
    (email_delivery.DELIVERY_CONFIGURATION_ERROR, None, 'check the email settings'),
    (email_delivery.DELIVERY_RATE_LIMITED, 429, 'limited sending'),
    (email_delivery.DELIVERY_TEMPORARY_FAILURE, 503, 'temporarily unavailable'),
    (email_delivery.DELIVERY_PERMANENT_FAILURE, 400, 'sender and recipient settings'),
    (email_delivery.DELIVERY_TIMEOUT, None, 'check the provider delivery log'),
    (email_delivery.DELIVERY_MALFORMED_RESPONSE, None, 'check the provider delivery log'),
])
def test_delivery_errors_explain_the_failure_without_leaking_provider_details(mail, caplog, code, http_status, guidance):
    db, provider, _ = mail
    def fail(_):
        raise email_delivery.EmailDeliveryError('secret key and recipient ada@college.edu', code=code,
                                                provider_status_code=http_status)
    provider.send_invitation = fail
    result = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert result['status'] == 'failed' and guidance in result['message']
    assert 'student is already registered' in result['message']
    assert db.deliveries[REGISTRATION] == 'failed' and not db.writes
    assert code in caplog.text
    assert 'secret key' not in str(result) + caplog.text
    assert 'ada@college.edu' not in str(result) + caplog.text


def test_mailgun_authentication_failure_can_be_retried_after_config_is_fixed(mail, monkeypatch, caplog):
    db, _, _ = mail
    requests = []
    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(401, text='private provider response')
        return httpx.Response(200, json={'id': '<accepted@mailgun.example>'})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        transport = email_delivery.MailgunEmailTransport(api_key='private-test-key', domain='college.example',
                                                        base_url='https://api.eu.mailgun.net', client=client)
        provider = email_delivery.ProductionEmailProvider(provider_name='mailgun', from_address='noreply@college.example',
                                                          api_key='private-test-key', transport=transport, max_retries=0)
        monkeypatch.setattr(email_delivery, 'get_email_provider', lambda: provider)
        failed = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
        assert failed['status'] == 'failed' and 'HTTP 401' in failed['message']
        assert len(requests) == 1 and db.deliveries[REGISTRATION] == 'failed'
        assert service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))['status'] == 'sent'
        assert service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))['status'] == 'already_sent'
    assert len(requests) == 2 and not db.writes
    for secret in ('private-test-key', 'private provider response', 'ada@college.edu'):
        assert secret not in str(failed) + caplog.text


def test_missing_provider_configuration_reports_setup_guidance(mail, monkeypatch):
    db, _, _ = mail
    def unconfigured():
        raise email_delivery.EmailDeliveryError('private config error', code=email_delivery.DELIVERY_CONFIGURATION_ERROR)
    monkeypatch.setattr(email_delivery, 'get_email_provider', unconfigured)
    result = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert result['status'] == 'failed' and 'check the email settings' in result['message']
    assert 'private config error' not in str(result)
    assert db.deliveries[REGISTRATION] == 'failed' and not db.writes


def test_local_capture_is_never_reported_as_real_delivery(mail):
    _, provider, _ = mail
    provider.name = 'local'
    result = service.send_invitation(principal(), UUID(SECTION), UUID(REGISTRATION))
    assert result['status'] == 'captured' and 'not been delivered' in result['message']


@pytest.mark.parametrize('email', [None, '', '  ', 'not-an-email'])
def test_new_registrations_require_valid_email(email):
    with pytest.raises(ValidationError):
        StudentRegistrationCreate(student_name='Ada', register_number='CS001', batch_id=BATCH, email=email)


def test_no_email_is_sent_without_explicit_opt_in_and_failed_delivery_preserves_the_save(mail, monkeypatch):
    db, _, messages = mail
    request = StudentRegistrationCreate(student_name='Ada', register_number='CS002', batch_id=BATCH, email='ada@college.edu')
    student_registrations.create_registration(principal(), UUID(SECTION), request)
    assert not messages and not db.rpc_calls
    assert 'auto_send_invitation' not in db.writes[0][1]
    def unavailable(*_args, **_kwargs): raise RuntimeError('mail unavailable')
    monkeypatch.setattr(service, 'send_invitation', unavailable)
    result = student_registrations.create_registration(principal(), UUID(SECTION), request.model_copy(update={'auto_send_invitation': True}))
    assert result['invitation_delivery']['status'] == 'failed'
    assert len(db.writes) == 2 and all(table == 'student_registrations' for table, _ in db.writes)


def test_auto_send_is_called_only_when_checked(mail, monkeypatch):
    _, _, _ = mail
    called = []
    def send(*args, **kwargs):
        called.append((args, kwargs))
        return {'status': 'sent'}
    monkeypatch.setattr(service, 'send_invitation', send)
    request = StudentRegistrationCreate(student_name='Ada', register_number='CS002', batch_id=BATCH, email='ada@college.edu', auto_send_invitation=True)
    result = student_registrations.create_registration(principal(), UUID(SECTION), request)
    assert result['invitation_delivery']['status'] == 'sent' and len(called) == 1
    assert called[0][0][2] == UUID(REGISTRATION)
