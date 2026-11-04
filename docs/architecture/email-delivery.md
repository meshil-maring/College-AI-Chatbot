# Gmail SMTP for student invitation links

Student setup links now support Gmail SMTP. Mailgun remains available for a
later configuration switch through the same shared provider API.

## Setup

1. Enable Google 2-Step Verification for the sending account.
2. Create a [Google App Password](https://myaccount.google.com/apppasswords) for
   CollegeAIChatbot. Use this password without display spaces, not your normal
   login password. Organization policy may restrict App Password availability.
3. Set backend secrets in `backend/.env` locally or deployment secret settings:

```dotenv
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-sender@gmail.com
SMTP_PASSWORD=your-google-app-password
EMAIL_FROM=your-sender@gmail.com
EMAIL_BASE_URL=http://localhost:5173
EMAIL_ALLOW_LIVE_IN_DEVELOPMENT=true
```

Use the Gmail account as the sender, or a Google-authorized alias.
`EMAIL_REPLY_TO` is optional. SMTP needs no `MAILGUN_*` or `EMAIL_PROVIDER_API_KEY`.
Other application settings remain required. Never commit credentials or expose
them via frontend `VITE_*` settings. See [Google's App Password instructions](https://support.google.com/accounts/answer/185833).

Run `uv sync --frozen` in `backend/`, then restart the backend. Development
captures email until the live-development flag is enabled; test/testing always
captures. For students using other devices, set `EMAIL_BASE_URL` to your public
frontend URL. Deployments require HTTPS and outbound DNS/TCP 587 access.

## Student workflow

Use the existing administrator student invitation interface to create, bulk
import, correct an email or resend an invitation. The email includes the
single-use `/student-setup#<token>` link. The student opens it, sets a password
and then uses the existing student sign-in page.

Existing 10-minute expiry, hashed tokens, rotation, resend limits, setup claims,
institution scope and atomic activation remain unchanged. Possession of the
emailed invitation remains this workflow's ownership proof. Sending mail never
verifies ownership or approves an account.

Request/response shapes are unchanged for:

- `POST /api/v1/admin/students/onboarding-invitations`
- `POST /api/v1/admin/students/onboarding-invitations/bulk`
- `PATCH /api/v1/admin/students/onboarding-invitations/{invitation_id}`
- `POST /api/v1/admin/students/onboarding-invitations/{invitation_id}/resend`
- `POST /api/v1/student-onboarding/inspect`
- `POST /api/v1/student-onboarding/complete`

`sent` means accepted provider submission, never confirmed inbox delivery.
In local/test capture mode it means captured in memory, without sending.
Failed submissions use existing `failed` delivery records; administrators can
resend. SMTP provides no inbox-delivery webhook here.

## Supabase Auth emails and OTP

Backend `.env` changes do not configure Supabase Auth. Signup confirmation and
`/api/v1/auth/forgot-password` continue using Supabase's email and verification
contracts. Manually configure custom SMTP in Supabase Authentication email
settings with the same Gmail host, port, username, App Password and sender.
Configure site/allowlisted redirect URLs, `AUTH_RECOVERY_REDIRECT_URL` and
confirmation/recovery templates there. Hosted settings are not changed here.
Supabase's default sender restricts recipients; custom SMTP is required for Auth
email outside the project team. See [Supabase custom SMTP](https://supabase.com/docs/guides/auth/auth-smtp).

Checked-in local Supabase settings use Mailpit, disable confirmation, and set a
3,600-second OTP expiry and 1-second resend interval. Those existing development
defaults are not a production security guarantee. For deployments requiring OTP,
enable confirmation, set expiry to 300 seconds, choose a cooldown such as 60
seconds, and configure email/verification budgets using [Supabase rate limits](https://supabase.com/docs/guides/auth/rate-limits).
Hashed OTP storage, per-code attempt limits and invalidation remain owned by the
deployed Auth service and require verification there. No parallel OTP store is
introduced; existing authentication and recovery behavior is preserved.

## Delivery architecture

`email_delivery.py` retains the shared API. `ProductionEmailProvider` owns bounded
retry/backoff. `SmtpEmailTransport` uses asynchronous `aiosmtplib`, mandatory
STARTTLS, certificate validation, authentication and multipart HTML/plain text.
A total deadline covers connection, TLS, login and DATA. Connections always
close; failed QUIT cannot turn an accepted submission into a retry. See the
[aiosmtplib API](https://aiosmtplib.readthedocs.io/en/stable/reference.html).

Existing sync FastAPI endpoints run in worker threads. Async callers can await
`ProductionEmailProvider.send_invitation_async`, keeping provider work and retry
sleeps outside the ASGI event loop. SMTP exposes its native async method too.

SMTP has no idempotent send API. Pre-submission connection errors and explicit
temporary SMTP rejections can retry within existing limits. DATA-stage timeout
or disconnect means uncertain acceptance and is not retried automatically.
Check the recipient's inbox before manually resending.

Logs contain safe event names, providers, timings and failure categories, without
recipients, credentials, OTPs, message bodies or invitation tokens. Configuration
and provider errors follow existing failed-delivery recording. No database
migration is required. Admin/staff/faculty invitations also use the shared provider;
their existing encrypted outbox still requires a deployment
`EMAIL_OUTBOX_TOKEN_ENCRYPTION_KEY` and worker scheduler. Student setup remains
inline with its existing invitation/status records.

Shared HTML rendering escapes content and preserves plain text. Templates cover
verification, registration receipt, invitation codes, recovery, approval,
rejection and staff notifications. Student setup and admin/staff/faculty invites
use the shared renderer. Templates do not enable new registration/approval
notification triggers; Supabase-generated messages use Supabase templates.

## Troubleshooting and scaling

- Authentication error: check Gmail username, App Password and Google policy.
  Changing the Google account password revokes its App Passwords.
- Timeout: check DNS, firewall and outbound port access.
- TLS error: use port 587 and valid system CA certificates. This STARTTLS
  adapter rejects port 465, which requires implicit TLS.
- Accepted message missing: check Spam, sender identity, bounces and quotas.
- No email locally: check environment and the live-development flag.
- Recovery/confirmation missing: configure Supabase custom SMTP separately.

Personal Gmail can reject sending above 500 messages/day, with additional
recipient/account restrictions. Review [Gmail limits](https://support.google.com/mail/answer/22839)
and [Workspace limits](https://support.google.com/a/answer/166852).
Use Gmail for low-volume initial use and check capacity before large imports.

## Mailgun later

Set `EMAIL_PROVIDER=mailgun` plus `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, US/EU
`MAILGUN_BASE_URL`, `MAILGUN_WEBHOOK_SIGNING_KEY` and verified-domain `EMAIL_FROM`.
Keep the existing worker/webhook setup; SMTP settings can then be removed.
Mailgun sandbox domains retain authorized-recipient requirements. Use a verified
sending domain for application recipients. Change Supabase Auth custom SMTP
separately if it should also use Mailgun.

Real delivery is untested until credentials are configured and an explicitly
authorized manual test succeeds. No real email is sent during implementation or
automated testing.
