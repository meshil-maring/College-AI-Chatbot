# Phase 7.18 — Mailgun Production Email Adapter & Webhook Reliability

## Status

**COMPLETE.** Mailgun is the only registered production email provider. No
production credential, real email, remote webhook, or remote database was used.

## Architecture

```text
invitation / resend
  -> email_outbox (authoritative pending work)
  -> Phase 7.17 lease/attempt worker
  -> provider-neutral EmailDeliveryProvider
  -> MailgunEmailTransport
  -> Mailgun HTTP Messages API
  -> normalized provider message ID
  -> POST /api/v1/webhooks/mailgun
  -> Mailgun signature + timestamp verification
  -> durable replay/event deduplication
  -> message-ID reconciliation
  -> outbox + safe invitation delivery projection
```

Request handlers never contact Mailgun. They atomically create/rotate the
invitation and enqueue an encrypted delivery payload. The existing worker is
the only production submission path.

## Configuration

Production selects `EMAIL_PROVIDER=mailgun` and supplies these backend-only
values through deployment secrets/configuration:

- `MAILGUN_API_KEY`
- `MAILGUN_DOMAIN`
- `MAILGUN_BASE_URL` (`https://api.mailgun.net` for US or
  `https://api.eu.mailgun.net` for EU)
- `MAILGUN_WEBHOOK_SIGNING_KEY`
- `MAILGUN_WEBHOOK_TOLERANCE_SECONDS` (default 900, bounded 30–3600)
- `EMAIL_FROM`
- optional `EMAIL_REPLY_TO`

The existing `EMAIL_BASE_URL`, provider timeout/retry settings, outbox Fernet
key, worker lease settings, and durable retry limit remain in force. Startup
fails closed outside local/test unless the selected provider is exactly
`mailgun`, all required Mailgun values exist, and both application and Mailgun
origins are credential-free HTTPS origins. Secret values never appear in the
validation report.

Local/development and test/testing environments continue to select capture
providers and require no real Mailgun account or key.

## Sending API adapter

`MailgunEmailTransport` implements the existing `ProductionEmailTransport`
contract. It sends multipart form data using HTTP Basic authentication with
username `api` to:

```text
{MAILGUN_BASE_URL}/v3/{MAILGUN_DOMAIN}/messages
```

It preserves the existing plain-text invitation content, configured sender,
optional reply-to, subject, recipient, invitation URL, expiry, and security
wording. No provider SDK is present in the frontend and no Mailgun-specific type
crosses the provider-neutral application boundary.

A successful HTTP 200 response must contain a non-empty JSON `id`. Angle
brackets are removed consistently from both send responses and webhook message
headers before persistence/correlation.

Error mapping is bounded and response bodies are never surfaced:

| Mailgun/API outcome | Normalized result | Retryable |
|---|---|---|
| 200 with valid `id` | submitted/sent | no further immediate call |
| 401/403 | configuration error | no |
| other 4xx | permanent failure | no |
| 429 | rate limited, bounded `Retry-After` | yes |
| 5xx | temporary failure | yes |
| network/protocol failure | temporary failure | yes |
| timeout | timeout/acceptance uncertain | yes |
| malformed 200 JSON/ID | malformed response | no |

## Submission versus delivery

`sent` means Mailgun accepted the HTTP submission and returned a message ID. It
does not mean the recipient server accepted the message. Only a verified,
correlated `delivered` event changes the safe delivery projection to
`delivered`.

Mailgun's Messages API does not document a general idempotency key for normal
email sends. Therefore a provider acceptance followed by a local timeout is
fundamentally ambiguous. The same durable outbox identity is retained across
bounded attempts, but it is not claimed as a Mailgun exactly-once key and is
not placed in delivered headers or user variables. A bounded retry can produce
a duplicate external email. The implemented guarantee is durable at-least-once
submission attempts with best-effort duplicate avoidance inside the database,
not exactly-once external delivery.

## Webhook verification

The route is `POST /api/v1/webhooks/mailgun`. It accepts Mailgun's JSON envelope
and follows the official signing procedure:

1. require `signature.timestamp`, `signature.token`, and
   `signature.signature`;
2. require an integer Unix timestamp, a 50-character token, and a 64-character
   hexadecimal signature;
3. reject timestamps outside the configured symmetric security window;
4. calculate `HMAC-SHA256(timestamp + token, webhook signing key)`;
5. compare with `hmac.compare_digest`;
6. require the payload domain to equal `MAILGUN_DOMAIN`;
7. hash (never persist) the raw signature token and consume its digest through
   the same transaction that records/reconciles the event.

Missing, malformed, stale, wrong-domain, and invalidly signed requests fail
closed before database access. Logs contain only safe categories.

Mailgun's documented signature authenticates `timestamp + token`; it does not
cryptographically hash the `event-data` object. HTTPS is therefore a required
transport security boundary. The implementation does not falsely claim payload
body signing; it additionally validates required event structure, configured
domain, message ID, and durable one-time use of the signed token.

Official references used:

- <https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/send-http>
- <https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages/post-v3--domain-name--messages>
- <https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks>
- <https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/webhook-payloads>
- <https://documentation.mailgun.com/docs/mailgun/user-manual/events/event-types>

## Event identity and replay protection

Mailgun documents event `id` as unique only within a day. The stable durable key
is SHA-256 over:

```text
mailgun NUL configured-domain NUL UTC-event-day NUL provider-event-id
```

`email_delivery_events` uniquely constrains `(provider_name, event_key)` and
also `(provider_name, replay_token_digest)`. Thus duplicate provider delivery,
concurrent webhooks, or reuse of one signed token can win at most one insert.
Raw tokens, signatures, signing keys, recipients, subjects, bodies, provider
diagnostics, and webhook payloads are not stored.

Unknown message IDs are recorded as `unknown_message` but update no outbox or
invitation. Unsupported events are recorded as `unsupported` and acknowledged
without state mutation.

## Correlation and tenant isolation

Reconciliation uses only the normalized Mailgun message ID plus provider name,
backed by the Phase 7.17 unique index. It never correlates by recipient,
subject, timestamp, invitation ID, or a client-supplied tenant. The resolved
outbox row determines its invitation and institution through existing foreign
keys, so one event updates at most that row. No webhook field selects a tenant.

`delivery_sequence` is a database-generated monotonic identity on outbox rows.
An event for an older resend generation may update that historical outbox row,
but cannot overwrite the invitation's current delivery projection. This closes
the late-old-message/resend race without changing token rotation semantics.

## Reconciliation state machine

The supported payload event mapping is:

| Mailgun event | Normalized event | State effect |
|---|---|---|
| `accepted` | accepted | no change (`sent` already records API acceptance) |
| `delivered` | delivered | `sent -> delivered` |
| `failed`, severity `temporary` | temporary failure | retain state; record safe category |
| `failed`, severity `permanent` | permanent failure | `sent/delivered -> bounced` |
| `rejected` | rejected | `sent/delivered -> bounced` if received |
| `complained` | complained | `sent/delivered -> complained` |
| other | unsupported | no change |

Terminal invitation delivery projection maps `delivered -> delivered` and
`bounced/complained -> failed`. The ordering is deliberately monotonic:

- late or duplicate delivery cannot turn `bounced` or `complained` into
  `delivered`;
- a delayed permanent failure may move a prior `delivered` event to `bounced`;
- no event moves work back to `pending` or `processing`;
- no event changes `dead_letter` or `cancelled`;
- temporary failure does not create a new application send because Mailgun
  manages its own temporary delivery retries;
- old-generation events do not replace a newer resend's invitation projection.

Webhook processing never rotates a token, activates/accepts an invitation,
creates an Auth user/password, or grants a role.

## Durable schema

Migration `20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql` adds:

- `email_outbox.delivery_sequence` and its unique index;
- service-role-only `email_delivery_events` with event and replay uniqueness,
  minimal normalized history, correlation, and processing results;
- `phase718_reconcile_mailgun_event`, which performs deduplication,
  correlation, monotonic transition, resend-generation isolation, and safe
  invitation projection in one database transaction.

Rollback planning: drop the reconciliation function, drop
`email_delivery_events`, then drop the sequence index/column. Phase 7.17 data
and provider-neutral architecture remain intact.

## Operations

Production prerequisites are:

1. verify the Mailgun sending domain and sender/DNS outside this repository;
2. store API, webhook signing, and Fernet keys in backend secret management;
3. choose the Mailgun US or EU API origin matching the domain region;
4. configure HTTPS webhooks for delivered, temporary failure, permanent
   failure, and complaint events at `/api/v1/webhooks/mailgun`;
5. run the existing `EmailOutboxWorker.process_once()` continuously or on a
   bounded schedule;
6. apply migrations through the approved deployment process only after local
   validation.

This implementation does not provision Mailgun, change DNS, configure a remote
webhook, start a production worker, apply a remote Supabase migration, or send a
real email.

## Verification

- Focused Phase 7.15–7.18 regression: **166 passed, 12 skipped**.
- Final Mailgun-only rerun: **27 passed**.
- Full backend: **2,426 passed, 27 skipped**.
- Frontend: **510 passed across 58 files**. Existing React `act(...)` warnings
  remain warnings only.
- Standalone TypeScript project typecheck: **passed**.
- Frontend production build: **passed** (112 modules transformed).
- Python compile check: **passed**.
- Local Supabase reset: **passed**, **22/22** migrations through
  `20261002010000`.
- Phase 7.18 rollback-only webhook behavior SQL: **passed**.
- Phase 7.17 rollback-only outbox/resend concurrency regression SQL: **passed**.
- Diff whitespace check: **passed**.
- Frontend source/bundle provider-secret scan: **clean**.
- Populated Mailgun secret/credential-shape scan outside tests: **clean**.
- Generated log scan after cleanup: **clean**.

Remote Supabase changed: **NO**. Production email sent: **NO**. Local Supabase
containers were stopped after validation.

