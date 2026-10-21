"""Explicitly requested student signup emails; no account or approval grants."""

import logging
from html import escape
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from postgrest.exceptions import APIError

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_rows
from app.services import email_delivery
from app.services.faculty_attendance import _assert_assigned

logger = logging.getLogger(__name__)


def _invitation_html(body: str, url: str) -> str:
    """Keep text/HTML content in sync and escape all saved student data."""
    href = escape(url, quote=True)
    paragraphs = []
    for paragraph in body.split('\n\n'):
        lines = []
        for line in paragraph.splitlines():
            if line == url:
                lines.append(
                    f'<a href="{href}" style="display:inline-block;margin:12px 0;padding:14px 22px;'
                    'background:#047857;color:#ffffff;text-decoration:none;border-radius:6px;'
                    'font-weight:bold">Complete registration</a><br>'
                    f'Or copy this link into your browser:<br><a href="{href}" style="color:#047857;word-break:break-all">{href}</a>'
                )
            else:
                lines.append(escape(line))
        paragraphs.append('<p style="margin:0 0 20px;line-height:1.6">' + '<br>'.join(lines) + '</p>')
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"></head>'
        '<body style="margin:0;padding:24px;background:#f3f4f6;font-family:Arial,sans-serif;color:#111827">'
        '<div style="max-width:600px;margin:0 auto;padding:28px;background:#ffffff;border-radius:10px">'
        '<h1 style="font-size:24px;margin:0 0 24px">Complete your student registration</h1>'
        + ''.join(paragraphs) + '</div></body></html>'
    )


def _delivery_failure_message(error: email_delivery.EmailDeliveryError) -> str:
    """Use fixed guidance, never provider response text or exception messages."""
    if error.code == email_delivery.DELIVERY_CONFIGURATION_ERROR:
        if error.provider_status_code == 401:
            message = ('The email provider rejected the sending credentials (HTTP 401). '
                       'Ask your administrator to check the sending API key, domain and region before retrying.')
        elif error.provider_status_code == 403:
            message = ('The email provider denied sending permission (HTTP 403). '
                       'Ask your administrator to check the sending key permissions and domain before retrying.')
        else:
            message = ('Invitation email is not configured correctly. '
                       'Ask your administrator to check the email settings before retrying.')
    elif error.code in {email_delivery.DELIVERY_TIMEOUT, email_delivery.DELIVERY_MALFORMED_RESPONSE}:
        message = ('The email provider did not confirm delivery. '
                   'Ask your administrator to check the provider delivery log before retrying.')
    elif error.code == email_delivery.DELIVERY_RATE_LIMITED:
        message = 'The email provider has limited sending. Try sending the invitation again later.'
    elif error.code == email_delivery.DELIVERY_TEMPORARY_FAILURE:
        message = 'The email provider is temporarily unavailable. Try sending the invitation again later.'
    else:
        message = ('The email provider rejected this invitation. '
                   'Ask your administrator to check the sender and recipient settings before retrying.')
    return message + ' The student is already registered.'


def _rpc(db, name, params):
    try:
        data = db.rpc(name, params).execute().data
    except APIError as error:
        if error.code in {'PGRST202', 'PGRST205', '42P01', '42883'}:
            raise AppError('Invitation delivery needs the student email database update. The student record is saved.',
                           503, 'STUDENT_INVITATION_SCHEMA_UNAVAILABLE') from error
        raise
    if isinstance(data, list):
        data = data[0] if data else None
    return data


def send_invitation(user: dict, section_id: UUID, registration_id: UUID, *, permission='attendance.manage') -> dict:
    scope = _assert_assigned(user, section_id, permission)
    tenant = str(user['institution_id'])
    db = get_admin_client()
    query = (db.table('student_registrations').select('*').eq('institution_id', tenant)
             .eq('registration_id', str(registration_id)).eq('section_code', scope.get('section_code') or scope['code']))
    for key in ('program_id', 'academic_year_id', 'semester_id'):
        query = query.eq(key, str(scope[key]))
    rows = read_rows(query.range(0, 0))
    if not rows:
        raise AppError('Student registration not found in this class.', 404, 'REGISTRATION_NOT_FOUND')
    row = rows[0]
    try:
        recipient = validate_email(row.get('email') or '', check_deliverability=False).normalized
    except EmailNotValidError as error:
        raise AppError('This registration needs a valid student email before sending an invitation.', 422, 'STUDENT_EMAIL_REQUIRED') from error
    institutions = read_rows(db.table('institutions').select('name, code').eq('institution_id', tenant)
                             .eq('is_active', True).range(0, 0))
    if not institutions or not institutions[0].get('code'):
        raise AppError('An active institution and registration code are required to send invitations.', 409, 'INSTITUTION_UNAVAILABLE')
    institution = institutions[0]
    base = settings.email_base_url.strip().rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise AppError('The application email URL is not configured correctly.', 503, 'EMAIL_BASE_URL_NOT_CONFIGURED')
    # This is the existing public signup route, not an authentication/approval token.
    url = f"{base}/login/student?{urlencode({'institution': institution['code'], 'register': '1'})}"
    result = lambda status, message: {'registration_id': str(registration_id), 'status': status, 'message': message}
    claim = _rpc(db, 'claim_student_registration_invitation', {
        'p_tenant': tenant, 'p_registration_id': str(registration_id), 'p_actor': str(user['user_id']),
    })
    if claim['status'] == 'sent':
        return result('already_sent', 'Invitation already sent. No additional email was sent.')
    if not claim.get('claimed'):
        return result('pending', 'Delivery is in progress or awaiting confirmation. If this persists, ask your administrator to check delivery before retrying.')
    status, provider, message = 'failed', '', 'The invitation could not be sent. Retry the email; the student is already registered.'
    try:
        delivery = email_delivery.get_email_provider()
        provider = str(getattr(delivery, 'name', 'unknown'))
        local_help = []
        if (parsed.hostname or '').lower().rstrip('.') in {'localhost', '127.0.0.1', '::1'}:
            local_help = [
                'This is a local test link. Open it on the computer running CollegeAI.',
                'If another account is signed in, open the link in a private browser window.', '',
            ]
        body = '\n'.join([
            f"Hello {row['student_name']},", '',
            f"You have been registered in Section {row['section_code']} at {institution['name']}.",
            f"Admission batch: {row['batch_start_year']}–{row['batch_end_year']}.",
            f"Register number: {row['register_number']}", '', 'Complete your student account registration:', url, '',
            *local_help,
            'Use the email address that received this invitation and your register number when signing up.',
            'Your institution will review your account before you can sign in.',
            'If you already have an account, sign in instead of creating another one.', '',
            'If you did not expect this email, contact your institution administrator.',
        ])
        email = email_delivery.InvitationEmail(
            to_email=recipient, subject=f"Complete your student registration at {institution['name']}",
            body=body, html_body=_invitation_html(body, url),
            institution_name=institution['name'], invitation_url=url, expires_at=None,
            idempotency_key=f"student-registration:{registration_id}",
        )
        outcome = delivery.send_invitation(email)
        provider = outcome.provider
        if outcome.status == email_delivery.DELIVERY_SENT:
            status = 'captured' if provider in {'local', 'test'} else 'sent'
            message = 'Email captured locally; it has not been delivered to the student.' if status == 'captured' else 'Invitation email accepted for delivery.'
    except email_delivery.EmailDeliveryError as error:
        message = _delivery_failure_message(error)
        code = error.code if error.code in email_delivery.SAFE_DELIVERY_FAILURE_CATEGORIES else 'UNKNOWN'
        http_status = error.provider_status_code if error.provider_status_code in {400, 401, 403, 404, 429, 500, 502, 503, 504} else None
        logger.warning('event=student_invitation_delivery_failed code=%s provider_http_status=%s', code, http_status)
    except Exception:
        # Never expose provider responses, credentials or recipient data in errors/logs.
        logger.warning('event=student_invitation_delivery_failed code=UNEXPECTED_ERROR')
    completed = _rpc(db, 'complete_student_registration_invitation', {
        'p_tenant': tenant, 'p_registration_id': str(registration_id),
        'p_attempt_id': claim['attempt_id'], 'p_status': status, 'p_provider': provider,
    })
    if not completed:
        return result('pending', 'Delivery status is being reconciled. Check again before retrying.')
    return result(status, message)
