# Phase 7.17 — Authorized Email Vendor Adapter, Durable Outbox Worker & Delivery Webhooks

## Phase status

**BLOCKED (provider-specific completion).** The provider-neutral durable outbox,
worker, retry, attempt history, dead-letter, token protection, invitation and
resend integration are implemented and validated. No email vendor is explicitly
authorized by repository configuration or project documentation, so the vendor
adapter, official webhook signature verification, provider event mapping, and
provider webhook endpoint are deliberately not implemented.

```text
Provider adapter: BLOCKED — no authorized vendor
Provider-specific implementation: BLOCKED
```

## 1. Provider authorization

The repository contains only placeholder provider names and the Phase 7.16
provider-neutral seam. References to AWS for object storage and commented local
Supabase SMTP examples are not authorization to select SES, SMTP, SendGrid,
Resend, Postmark, Mailgun, or another vendor. No inference was made from price,
popularity, installed libraries, or examples.

Authorized provider: **none**. Credentials configured by this change: **no**.
Real email sent: **no**.

## 2. Provider adapter

The existing `EmailDeliveryProvider` and `ProductionEmailTransport` contracts
remain the only delivery abstraction. `EmailDeliveryResult` now also carries a
normalized provider message ID, retryability, and bounded retry-after metadata.
`ProductionEmailProvider` passes through the normalized transport message ID.
Local/test capture generates a deterministic safe ID from the outbox identity.

`_build_production_transport` intentionally remains unregistered. There is no
vendor SDK, endpoint, response type, credential name, or signature algorithm in
the codebase.

## 3. Email outbox

Migration `20261002000000_phase_7_17_email_outbox_worker.sql` adds the minimum
durable objects:

- `email_outbox`: stable UUID, invitation reference, authenticated ciphertext,
  state, attempt count, schedule, lease, safe failure category, timestamps,
  provider name, and provider message ID;
- `email_delivery_attempts`: one bounded history row per outbox attempt;
- service-role-only RLS/grants, foreign keys, constraints, and claim/lease
  indexes.

The outbox state machine is constrained to `pending`, `processing`, `sent`,
`delivered`, `bounced`, `complained`, `dead_letter`, and `cancelled`. Worker
settlement permits only `processing -> sent | pending(retry) | dead_letter |
cancelled`. Provider webhook-ready states exist in storage, but no unauthenticated
webhook writes them without an authorized provider verifier.

## 4. Transaction boundary

`phase717_create_invitation_with_outbox` inserts the invitation and outbox row
inside one PostgreSQL function transaction. Either both are visible or neither
is. The HTTP request returns `email_delivery.status = pending`; it does not wait
for provider I/O.

`phase717_rotate_invitation_with_outbox` locks the invitation, validates its
pending state and row version, cancels old pending jobs, rotates the digest and
expiry, increments the resend count, resets delivery state, and inserts the new
outbox job in one transaction.

A partial unique index on `(institution_id, lower(email)) WHERE status='invited'`
also closes concurrent duplicate-invitation creation.

## 5. Worker and concurrency

`EmailOutboxWorker.process_once()` is the reusable execution boundary. The
repository still has no production scheduler or separate worker process, so a
deployment must invoke it continuously or on a schedule.

`phase717_claim_email_outbox` uses `FOR UPDATE ... SKIP LOCKED` and changes each
selected row to `processing` in the same transaction that creates its attempt
record. Two workers cannot successfully claim the same available job. Batch
size is bounded to 200.

The worker never grants a role, creates an Auth account, accepts an invitation,
or changes invitation authorization state. It only delivers and records email.

## 6. Stale lock recovery

`locked_at` is a database lease controlled by `EMAIL_WORKER_LOCK_SECONDS`.
Claiming first closes abandoned attempt records. A stale job below the retry
limit returns to `pending`; one at the limit becomes `dead_letter`. The
invitation roster projects a terminal delivery failure without changing the
invitation lifecycle.

## 7. Retry and dead-letter

The worker reuses the Phase 7.16 base/cap and retry-after semantics. Retryable
timeouts, temporary failures, and adapter-classified transient failures receive
capped exponential scheduling through `available_at`. There is no sleep or busy
loop in `process_once`. `EMAIL_OUTBOX_RETRY_LIMIT` bounds durable attempts.

Permanent failures, invalid protected payloads, and exhausted retries become
`dead_letter`. Only safe categories and timestamps are stored. Provider response
bodies, credentials, raw tokens, URLs, passwords, and stack traces are not
stored.

## 8. Idempotency and provider message IDs

Every provider call uses `email-outbox:{email_outbox.id}`. The identity is stable
across worker retries and contains no invitation credential. Successful
submission persists the normalized `provider_message_id` on both the outbox and
the attempt record. A future adapter must apply this identity using the selected
vendor's official idempotency facility or document/classify uncertain failures
as non-retryable.

## 9. Delivery state separation

Invitation lifecycle remains `invited | accepted | cancelled | expired`.
Delivery state remains independent. The roster supports `pending`, `sent`,
`delivered`, and `failed`; operational details remain server-side. Delivery
cannot accept an invitation, and bounce/failure cannot revoke or delete an
account.

Terminal invitation transitions cancel pending email jobs through a database
trigger. An already in-flight provider call may finish, but its invitation URL
is invalid whenever the invitation is terminal.

## 10. Resend integration and race safety

Resend creates a fresh random token, encrypted delivery secret, digest, expiry,
and outbox UUID. The transaction cancels all older pending jobs before inserting
the new one. The worker independently decrypts the protected secret and asks the
database to verify its SHA-256 digest is still the invitation's current digest
before rendering or sending.

A non-stale `processing` lease causes resend to return the existing safe
`INVITATION_NOT_RESENDABLE` conflict rather than rotating underneath a provider
call. Therefore:

- resend wins first: old pending jobs are cancelled and cannot be claimed;
- worker wins first: resend is refused until that lease settles or expires;
- crashed worker: the stale lease is recovered, after which resend can cancel it;
- no code path restores an old digest, so an old link can never become valid.

## 11. Token security

The invitation table still stores only the lowercase SHA-256 digest. The outbox
stores a Fernet-authenticated ciphertext named `protected_token`. The raw token
is never stored in plaintext and is recovered only in worker memory immediately
before current-digest validation and rendering. Production startup requires the
backend-only `EMAIL_OUTBOX_TOKEN_ENCRYPTION_KEY`; local/test uses an explicitly
non-production deterministic key.

The ciphertext and key never enter API schemas, frontend configuration, audit
details, or logs. The existing one-time response containing the newly generated
raw token remains unchanged for the operator fallback flow.

## 12. Webhooks and signature verification

No provider is authorized, so no official signature scheme can be selected and
no public webhook endpoint is exposed. A generic unauthenticated webhook would
violate the phase security gate. Consequently, no webhook event table is added
and no webhook-completion claim is made.

After vendor authorization, the adapter must add exactly one provider-specific
endpoint, verify the official signature over the required raw request bytes
before trusting event data, enforce replay protection, persist minimal provider
event IDs for idempotency, explicitly map supported events, and update only
delivery state by provider message ID.

## 13. Configuration

Configuration names only:

- `EMAIL_PROVIDER`
- `EMAIL_FROM`
- `EMAIL_REPLY_TO`
- `EMAIL_BASE_URL`
- `EMAIL_PROVIDER_API_KEY`
- `EMAIL_PROVIDER_TIMEOUT_SECONDS`
- `EMAIL_PROVIDER_MAX_RETRIES`
- `EMAIL_PROVIDER_RETRY_BASE_SECONDS`
- `EMAIL_PROVIDER_RETRY_CAP_SECONDS`
- `EMAIL_OUTBOX_TOKEN_ENCRYPTION_KEY`
- `EMAIL_WORKER_BATCH_SIZE`
- `EMAIL_WORKER_LOCK_SECONDS`
- `EMAIL_OUTBOX_RETRY_LIMIT`

Non-local startup fails closed without the outbox encryption key in addition to
the Phase 7.16 production email requirements. No secret value is documented.

## 14. Observability

Safe structured logs cover provider latency, successful submissions, scheduled
retries, dead letters, invalid payloads, and per-batch claimed/sent/retried/
dead-letter/cancelled totals. Attempt rows provide durable timing and outcomes.
No recipient, message body, invitation URL, token, ciphertext, provider response,
or secret is logged.

## 15. Frontend

The roster continues to show delivery independently from invitation lifecycle
and now labels `delivered`. Create/resend responses with `pending` show
“Invitation email queued” rather than claiming success or failure. Provider
diagnostics and credentials remain absent.

## 16. Tests

- Phase 7.17 focused + invitation/config regression: **192 passed**.
- Requested Phase 6.11 / 7.2 / 7.4 / 7.12–7.17 set: **336 passed, 12 skipped**.
- Full automated backend (`DEBUG=true`, `pytest -q tests`): an earlier complete
  run passed **2,398 passed, 27 skipped**. A final rerun encountered three
  pre-existing network-sensitive legacy tests attempting an external Supabase
  TLS connection; all three passed immediately in isolation (**3/3**). The
  Phase 7.17 touched none of those chat/student paths.
- Frontend production build (`tsc -b && vite build`): **passed**.
- Frontend full run: **502 passed**, with eight resource-sensitive failures in
  two files when all 58 jsdom files ran together. Both files passed immediately
  in isolation: `RegistrationForm` **25/25**, `App` **8/8**; therefore all 510
  tests have passing isolated evidence, but the monolithic run is not claimed
  green.
- Local rollback-only database behavior validation: **passed** (atomic create,
  resend cancellation, exclusive claim, active-lease race refusal, stale lock
  recovery, attempt history, settlement).

Automated tests use fake/local providers only. No test can send production mail.

## 17. Migration

- File: `20261002000000_phase_7_17_email_outbox_worker.sql`
- Ledger count: **21**
- Fresh local reset #1: **passed**
- Fresh local reset #2: **passed**
- Local migration ledger: **21/21 through Phase 7.17**
- Rollback-only behavioral SQL:
  `scripts/validation/phase717_local_outbox.sql` — **passed**
- Historical migrations modified: **no**
- Remote migration applied: **no**

## 18. Deployment requirements

1. Explicitly authorize one vendor before adding provider code.
2. Add one adapter below `ProductionEmailTransport` and verify idempotency.
3. Provision backend-only provider and Fernet keys.
4. Run `EmailOutboxWorker.process_once()` continuously or on a schedule with
   more than one instance only after exercising the database claim behavior.
5. Add the provider-specific verified webhook and minimal event-id persistence.
6. Configure sender/domain/DNS outside this repository under separate approval.

No production worker, vendor, webhook, sender domain, or deployment is claimed.

## 19. Known limitations

- No authorized provider, adapter, credentials, real submission, webhook
  endpoint, official signature verification, event idempotency, or delivery/
  bounce reconciliation exists yet.
- The application hosting setup does not supervise a continuous outbox worker;
  `process_once()` must be scheduled by deployment operations.
- Fernet key rotation/re-encryption is not implemented.
- The all-at-once frontend test run is resource-sensitive on this Windows host;
  the two affected files pass in isolation.

## 20. Remote safety

```text
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote users modified: NO
Remote institution data modified: NO
Remote invitation data modified: NO
Remote audit data modified: NO
Production email sent: NO
Production deployment: NO
DNS modified: NO
```

Only local Supabase containers were started, reset twice, validated, and stopped.

## 21. Recommended next phase

Authorize a specific email vendor, then complete the provider-dependent portion
as **Phase 7.18 — Authorized Vendor Adapter & Verified Delivery Webhook**. That
phase should register exactly one adapter, add official signature/replay checks,
persist minimal webhook event identities, reconcile delivered/bounced/complained
states, and run an explicitly authorized sandbox delivery test. Until the vendor
decision exists, provider-specific work remains blocked.
