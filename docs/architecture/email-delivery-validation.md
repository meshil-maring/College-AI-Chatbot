# Gmail SMTP implementation validation

Date: 2026-11-03. Scope: Gmail delivery for existing student setup/sign-in
invitations and the shared invitation provider, preserving Mailgun for later use.

## IMPLEMENTED

- Gmail STARTTLS SMTP using `aiosmtplib`, certificate validation, App Password
  authentication, HTML/plain text, connection cleanup and a total timeout.
- Provider selection with `EMAIL_PROVIDER=smtp` or `mailgun`. Local capture and
  the explicit live-development opt-in remain; tests always capture by selection.
- Existing student create/import, corrected-email and resend workflows reuse the
  SMTP provider. Existing admin/staff/faculty invitation consumers share it too.
- Configuration validation during startup/service initialization, safe failure
  categories and existing delivery-status recording. SMTP acceptance is
  distinguished from inbox delivery in user-facing student invitation messages.
- Bounded safe retries. DATA timeout/disconnect is non-retryable because SMTP
  cannot guarantee idempotency after uncertain acceptance.
- Escaped branded HTML for setup and invitation emails, plus reusable content
  templates for verification, registration receipt, invitation codes, recovery,
  approval, rejection and staff notifications.
- Existing oversized settings/delivery modules split into focused modules to
  comply with the 250-line limit while retaining their public import contracts.

## Files inspected

- Root/backend `AGENTS.md`, backend `STRUCTURE.md`, core/services module guides.
- `backend/app/config.py`, startup email checks, `backend/.env.example`,
  `backend/pyproject.toml`, and the dependency lock.
- Email delivery, outbox worker/encryption, Mailgun transport/webhooks and their
  existing email, configuration and security regression tests.
- Student onboarding delivery, management, acceptance, repositories, schemas,
  administrator/public routes and student onboarding tests.
- Signup, student registration, password recovery and invitation email ownership
  contracts; existing sign-in and registration/recovery security tests.
- Local `supabase/config.toml` and checked-in student onboarding migration
  contracts. No hosted database access or migration execution occurred.

## Files created or modified

| Location | Files |
| --- | --- |
| `backend/` | `.env.example`, `README.md`, `pyproject.toml`, `uv.lock` |
| `backend/app/` | `config.py` |
| `backend/app/core/` | `README.md`, `startup_validation/email.py` |
| New `backend/app/core/configuration/` | `__init__.py`, `email.py`, `smtp.py`, `validation.py` |
| `backend/app/services/` | `README.md` |
| `backend/app/services/email/` | Modified `email_delivery.py`; new `capture.py`, `contracts.py`, `production.py`, `mailgun_transport.py`, `smtp_transport.py`, `invitation_messages.py`, `templates.py` |
| `backend/app/services/invitations/` | `student_onboarding_email.py` |
| `backend/tests/` | `test_phase_7_16_production_email_delivery.py` |
| New `backend/tests/email/` | `conftest.py`, `test_smtp_configuration.py`, `test_smtp_transport.py`, `test_student_setup_delivery.py`, `test_templates.py` |
| `docs/architecture/` | `email-delivery.md`, this validation report |

Mailgun's HTTP adapter, configuration, webhook verification/reconciliation and
tests are retained for the requested later switch. No Mailgun SDK dependency
existed; the existing `httpx` dependency remains shared. `aiosmtplib==5.1.3` was
added to the resolved lock under the `>=5.0,<6` dependency constraint.

## Configuration and endpoints

Required SMTP settings: `EMAIL_PROVIDER=smtp`, `SMTP_HOST=smtp.gmail.com`,
`SMTP_PORT=587`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, and a usable
`EMAIL_BASE_URL`. Optional `EMAIL_REPLY_TO`; local live sending requires
`EMAIL_ALLOW_LIVE_IN_DEVELOPMENT=true`. Existing outbox deployments still need
`EMAIL_OUTBOX_TOKEN_ENCRYPTION_KEY` and their worker scheduler.

Existing administrator student invitation create, bulk, corrected-email and
resend endpoints now submit through the selected provider. Public student
inspect/complete endpoint shapes and authentication/authorization rules remain
unchanged. Existing admin/staff/faculty invitation delivery uses the shared
provider. Password recovery still delegates to Supabase Auth. Full endpoint
paths and deployment instructions are in the [setup guide](email-delivery.md).

## Security

No credentials are hardcoded or returned to the frontend. SMTP passwords are
excluded from settings repr. Message construction rejects invalid recipients
and header injection. TLS is mandatory; no plaintext fallback is permitted.
Logs omit bodies, recipients, passwords, codes and tokens.
Existing invitation tokens remain hashed, expiring, single-use and rotated on
resend. Sending email never marks ownership verified. Existing approval, tenant,
RBAC, rate-limit and recovery-session protections remain unchanged.

## TESTED

All tests use mocked providers/SMTP; no real mail is sent.

| Check | Result | Evidence |
| --- | --- | --- |
| SMTP/template/student delivery plus existing live-development, production-provider and configuration tests | 99 passed | `logs/backend/smtp-focused-tests.log` |
| Existing invitation verification, outbox, Mailgun/webhooks, Auth security, student onboarding/sign-in, acceptance, registration recovery/errors, student approval journey and backend structure tests | 377 passed | `logs/backend/smtp-regression-tests.log` |
| Offline backend structure validator | Passed | `logs/backend/smtp-structure.log` |
| Changed Python file sizes and feature-folder counts | Passed | `logs/backend/smtp-maintenance-limits.log` |
| `git diff --check` | Passed | Local verification |

Total: 476 passing tests. The existing Starlette/httpx deprecation warning remains.
Checks ran with `DEBUG=false`, `ENVIRONMENT=test`, and live-development email
disabled; individual email tests explicitly opt into their mocked SMTP provider.
Pytest cache/temp directories are under `logs/backend/` to avoid host temp access.

SMTP tests cover configuration presence and port bounds, successful submission,
authentication/connect/TLS failures, recipient refusals, text/HTML, injection,
cleanup, async usage, bounded retries, uncertain acknowledgement, privacy and
student workflow success/failure recording. Existing regressions cover email
ownership transitions, expiration/resend/rate controls and recovery security.

All newly added code folders contain at most 15 direct files; changed Python
files are at most 250 lines. Existing oversized `backend/tests/` has no new
direct files; new tests are grouped in `tests/email/`.

## NOT TESTED

- Real Gmail submission, inbox arrival, spam placement, account quotas or
  production firewall connectivity.
- Hosted Supabase custom SMTP, OTP generation/hash storage, per-code maximum
  attempts, expiry, resend cooldown or delivery. Those are Auth-provider
  responsibilities, not implemented by this SMTP transport.
- Full frontend/browser suite and the full backend suite; focused relevant
  backend regressions were run instead. No frontend files changed.

New registration/approval/rejection notification triggers are outside this
student invitation change. Their reusable templates are implemented and tested;
adding templates does not enable new email side effects. Existing Supabase-owned
confirmation/OTP/recovery emails keep their provider contracts.

## REQUIRES MANUAL CONFIGURATION

Configure Gmail credentials and public frontend URLs, restart the backend, and
perform an explicitly authorized manual recipient test. Until then real delivery
is unverified. Configure Supabase Auth custom SMTP separately for confirmation
and recovery. Review production OTP confirmation, five-minute expiry, cooldown
and attempt/rate policies there; local defaults are documented in the setup guide.
For larger volume, configure the retained Mailgun adapter with a verified domain.

## BLOCKED

No implementation or offline validation is blocked. A full `uv sync --frozen`
attempt could not replace the currently running Windows `start.exe`. The locked
SMTP package was installed directly into the existing virtual environment for
tests. Stop/restart that backend process and rerun `uv sync --frozen` when
refreshing the complete environment. No process was terminated automatically.
