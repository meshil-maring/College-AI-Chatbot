# Phase 7.16 — Production Email Provider & Delivery Reliability

## Phase status

**COMPLETE (provider-neutral boundary).** No production email vendor is selected
or configured in this repository. Phase 7.16 therefore implements and tests the
reliable production boundary permitted by the acceptance criteria, while real
production delivery remains fail-closed until a vendor adapter is authorized.

## 1. Objective

Extend the Phase 7.15 `EmailDeliveryProvider` without changing invitation
authorization. The invitation row is committed before external I/O, delivery
state is recorded independently of invitation lifecycle, and failure never
creates an Auth account, grants a role, accepts an invitation, or restores an
old token.

## 2. Provider selection

Repository inspection found no approved email vendor. `boto3` is already used
for object storage and is not evidence that AWS SES was selected. No SendGrid,
Resend, SES, Mailgun, SMTP, or other integration was introduced.

Selection is environment-first:

- `development`, `dev`, `local`: `LocalEmailProvider` (bounded memory capture).
- `test`, `testing`: `TestEmailProvider` (deterministic capture).
- every other environment: `ProductionEmailProvider`; it never falls back to a
  capture provider, even when `EMAIL_PROVIDER=local` is accidentally supplied.

## 3. Provider abstraction

The existing `EmailDeliveryProvider.send_invitation(InvitationEmail)` contract
remains the invitation service boundary. A smaller
`ProductionEmailTransport` protocol is the vendor adapter seam beneath it. A
future adapter receives the already-rendered message, sender, optional reply-to,
timeout, and idempotency key. It does not decide institution, role, expiry,
token, invitation state, or authorization.

The vendor registration function intentionally returns no transport today.
Production delivery therefore returns `DELIVERY_CONFIGURATION_ERROR` and never
pretends an email was sent.

## 4. Configuration

Backend runtime variables:

- `ENVIRONMENT`
- `EMAIL_PROVIDER`
- `EMAIL_FROM`
- `EMAIL_REPLY_TO` (optional)
- `EMAIL_BASE_URL`
- `EMAIL_PROVIDER_API_KEY`
- `EMAIL_PROVIDER_TIMEOUT_SECONDS`
- `EMAIL_PROVIDER_MAX_RETRIES`
- `EMAIL_PROVIDER_RETRY_BASE_SECONDS`
- `EMAIL_PROVIDER_RETRY_CAP_SECONDS`

Non-local startup validation requires an explicit non-capture provider,
`EMAIL_FROM`, the provider key, and an HTTPS `EMAIL_BASE_URL` without embedded
credentials. Validation output contains names and value-free status only.
Local/test startup does not require production email configuration.

## 5. Secret handling

The provider credential is read only from backend settings into a private
attribute. It is absent from API schemas, frontend variables, audit payloads,
logs, rendered messages, fixtures, and documentation values. `.env.example`
contains only empty or descriptive placeholders. `.env` remains ignored.

## 6. Email contract

Phase 7.15 rendering is preserved: institution name, University Administrator
context, configured-origin invitation URL, expiry, one-time/bound-email text,
and safe ignore text. The message contains no password, token hash, database
identifier, provider credential, or authorization detail. The raw token exists
only within the invitation URL required by the recipient.

## 7. Timeout

Every production transport call receives an explicit timeout. Default:
`10 seconds`; valid configured range: greater than zero through 60 seconds.
`TimeoutError` maps to `DELIVERY_TIMEOUT`. Stack traces and provider response
bodies are not returned to users.

## 8. Retry policy

The default is at most two retries after the initial request (three total
calls). Retry delays use capped exponential backoff: 0.25 seconds base and 2
seconds maximum by default.

Retryable failures are timeout, temporary network failure, and an adapter
error explicitly marked retryable (for example a safe 5xx mapping). Permanent
provider rejection, credentials/sender configuration errors, malformed
responses, and other non-retryable adapter errors are attempted once. A rate
limit can carry `retry_after_seconds`; the boundary honors it only within the
same retry budget and caps the delay. There is no infinite loop.

## 9. Idempotency

The application identity is:

```text
admin-invitation:{invitation_id}:{delivery_attempt}
```

It never contains the raw token. The exact same value is supplied on every
provider retry for that attempt. A vendor adapter must apply it through the
vendor's idempotency facility. If a vendor cannot make a failure safe to retry,
the adapter must classify that failure as non-retryable.

## 10. Delivery state

No new schema was required. Phase 7.15 already provides `pending`, `sent`, and
`failed`, timestamp, attempt count, resend count, and last-sent timestamp.
Before external I/O the row is committed as `pending`; after the call it is
updated to `sent` or `failed`, and the attempt counter is updated. These fields
remain separate from `invited`, `accepted`, `cancelled`, and `expired`.

No database transaction remains open during the provider request. If the
process stops between state writes, `pending` truthfully indicates an uncertain
attempt and a controlled resend can recover it.

## 11. Failure handling

Safe categories are:

- `DELIVERY_TEMPORARY_FAILURE`
- `DELIVERY_PERMANENT_FAILURE`
- `DELIVERY_CONFIGURATION_ERROR`
- `DELIVERY_TIMEOUT`
- `DELIVERY_RATE_LIMITED`
- `DELIVERY_MALFORMED_RESPONSE`

Failures leave the invitation pending in its lifecycle and persist failed
delivery state. They create no user, role, acceptance, or tenant access. The UI
uses: `Invitation could not be delivered. Try again later.`

## 12. Resend integration

Resend first checks Super Admin authorization, tenant binding, lifecycle state,
expiry, and existing application rate limits. It generates a new token and
atomically overwrites the old digest. The rotation also compares the previously
read `updated_at`, so concurrent resends of one version have one winner. Only
after that commit does delivery begin.

If delivery fails, the new invitation state and digest remain; the old digest
is not restored. Thus the old URL stays invalid and a later controlled resend
can rotate again.

## 13. Rate limits

Phase 7.15 inspection, acceptance, per-invitation, per-institution, per-actor,
and per-IP resend limits remain unchanged. Provider rate limiting is separately
mapped to `DELIVERY_RATE_LIMITED` and uses bounded, capped retry-after handling.

## 14. Logging

Logs contain only event name, provider name, safe category, attempt count,
bounded delay, and duration. They do not contain recipient, subject/body, raw
token, token hash, password, provider key, Authorization header, or invitation
URL. Regression tests specifically assert that `/admin-invite/{raw-token}` is
absent.

## 15. Audit

Existing `institution_admin_invitation_email_sent` and
`institution_admin_invitation_email_failed` events are reused. Details contain
invitation reference, institution association from the audit row, provider,
delivery status, and safe failure category when failed. Retry telemetry is a
safe operational log event; no schema expansion was needed.

## 16. Concurrency

Phase 7.14's conditional atomic invitation claim still guarantees one accepted
account. Resend remains conditional on `status='invited'` and now includes an
optimistic row-version comparison. Delivery retries share one idempotency key.
No code path restores a superseded digest or changes a terminal invitation back
to pending.

## 17. Tests

`test_phase_7_16_production_email_delivery.py` uses fake transports only and
covers environment selection, production no-fallback, startup failure, success,
timeout, temporary recovery, permanent failure, rate limit/retry-after,
malformed response, bounded retry, idempotency, health, and log secrecy.

Phase 7.15 and startup tests were updated for the explicit environment and safe
error taxonomy. Frontend tests verify honest success/failure messaging and the
existing frontend environment allowlist. No automated test can contact a real
email service.

## 18. Migration

No migration was needed. The repository still has **20 migrations**; the latest
is `20261001030000_phase_7_15_invitation_delivery_email_verification.sql`.
Phase 7.15 already represents the minimum durable delivery state. No historical
migration was edited and no local or remote migration was applied.

## 19. Known limitations

- No production vendor is selected, so no real vendor adapter exists and
  production invitation delivery intentionally fails closed.
- Delivery remains synchronous at the HTTP service boundary; there is no
  durable worker/outbox for automatic background recovery after process death.
- Phase 7.15 application rate-limit counters remain process-local.
- Provider message IDs and bounce/webhook lifecycle are not persisted because
  no provider contract has been selected.

## 20. Remote safety

No remote database, Supabase Auth, users, institutions, invitations, audit data,
email provider, deployment, or DNS was accessed or changed. No production email
was sent.

## 21. Production deployment requirements

Do not claim production email readiness yet. First authorize one vendor, add
one `ProductionEmailTransport` adapter, register only that exact
`EMAIL_PROVIDER` value, supply secrets through backend runtime configuration,
verify sender/domain ownership and DNS outside this change, and run a separately
authorized sandbox delivery test. The adapter must preserve this phase's
timeout, safe category, retry, idempotency, logging, and response contracts.

Recommended next phase: **Phase 7.17 — Authorized Email Vendor Adapter,
Durable Outbox Worker & Delivery Webhooks**.
