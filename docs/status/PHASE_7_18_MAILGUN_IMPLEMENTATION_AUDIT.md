# Phase 7.18 — Pre-Implementation Audit

This note records the Phase 7.15–7.17 delivery boundary before Mailgun-specific
code is added.

1. **Current email delivery boundary:** invitation content is rendered by
   `app.services.email_delivery`; application code depends on
   `EmailDeliveryProvider`, with vendor I/O isolated behind
   `ProductionEmailTransport`. Local/test providers capture without network I/O.
2. **Current outbox lifecycle:** invitation creation and resend atomically insert
   `email_outbox` work. Jobs move through `pending -> processing -> sent`,
   `pending` retry, `dead_letter`, or `cancelled`; webhook-ready terminal states
   already include `delivered` and `bounced`. Protected tokens are cleared on
   every terminal submission outcome.
3. **Current worker lifecycle:** `EmailOutboxWorker.process_once()` claims via a
   PostgreSQL `SKIP LOCKED` lease, records an attempt, decrypts and revalidates
   the current token digest, invokes the provider-neutral boundary, then settles
   the attempt. Expired leases are recovered by the claim function.
4. **Current invitation delivery state:** invitation authorization remains
   `invited | accepted | cancelled | expired`. Its separate safe delivery
   projection is `pending | sent | delivered | failed`; delivery never accepts
   an invitation or grants a role.
5. **Current retry behavior:** adapter retries and durable outbox retries are
   bounded, use capped exponential delay, and honor normalized retry-after
   values. Resend cancels stale pending work and refuses to rotate beneath an
   active worker lease.
6. **Current provider configuration:** local/test capture is selected by
   environment. Deployed environments require an explicit non-local provider,
   sender, provider key, HTTPS application base URL, and Fernet outbox key.
   No production transport is currently registered.
7. **Mailgun integration points:** register one `MailgunEmailTransport` in the
   existing production provider factory; add Mailgun-only server configuration
   and startup checks; mount one `/api/v1/webhooks/mailgun` router; persist a
   verified event identity and reconcile by normalized Mailgun message ID in a
   service-role database function. Invitation rendering, request handlers,
   transactional enqueueing, worker claims, and acceptance security remain
   unchanged.

Official semantics selected for implementation: HTTP Basic auth user `api`,
multipart `POST {MAILGUN_BASE_URL}/v3/{MAILGUN_DOMAIN}/messages`, success JSON
with a non-empty `id`, and JSON webhooks signed as HMAC-SHA256 over the exact
concatenation of signature `timestamp` and `token`. The webhook event `id` is
documented by Mailgun as unique only within a day, so the durable event key will
combine provider, configured domain, UTC event day, and event id before hashing.

