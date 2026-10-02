# Phase 7.15 — Invitation Delivery, Email Verification & Abuse Controls

**Status:** COMPLETE
**Scope:** Extend the Phase 7.14 University Admin invitation system with email
delivery, email-ownership verification, secure resend, rate limiting, expiry
cleanup and delivery-failure handling. The Phase 7.14 authorization model is
**not redesigned**.

---

## 1. Objective

Complete the delivery half of the invitation lifecycle so that an invitation is
not merely *creatable* but *deliverable*, *verifiable*, *reissuable* and
*defensible*:

```
Super Admin
    ↓
Invite University Admin
    ↓
Invitation created (Phase 7.14)
    ↓
Email delivery boundary          ← NEW in 7.15
    ↓
Admin receives invitation
    ↓
/admin-invite/{token}
    ↓
Invitation + email verification  ← NEW in 7.15
    ↓
Password setup
    ↓
Auth account
    ↓
Institution-scoped admin
```

## 2. Existing architecture (reused, not duplicated)

| Concern | Existing owner | Phase 7.15 decision |
| --- | --- | --- |
| Super Admin authorization | `require_super_admin` (7.12) | **Reused unchanged.** Every new platform route declares it. |
| Institution management | `platform_institutions` service/repo (7.13) | **Reused unchanged.** |
| Invitation model | `platform_admin_invitations` (7.14) | **Extended in place** — additive columns only, no second table. |
| Invitation service | `platform_admin_invitations.py` (7.14) | **Extended**; the 7.14 acceptance flow is untouched in shape. |
| Auth account creation | `_create_auth_account` (GoTrue) | **Reused unchanged.** |
| Role grant | `assign_user_role_scope` (6.13) | **Reused unchanged.** |
| Audit ledger | `platform_institution_audit_log` (7.13/7.14) | **Extended additively**; no new ledger. |
| Abuse controls | `SlidingWindowRateLimiter` (7.8) | **Primitive reused**, with a separate instance and separate budgets. |
| Email | *(none)* | **New boundary** — the only genuinely new subsystem. |

No authentication, authorization, tenancy or role system was duplicated.

## 3. Email abstraction

`backend/app/services/email_delivery.py` defines the boundary:

```python
class EmailDeliveryProvider(Protocol):
    name: str
    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult: ...
```

The invitation service depends **only** on this protocol. Vendor-specific logic
does not appear anywhere in the invitation service.

```
Invitation Service
       ↓
EmailDeliveryProvider (protocol)
       ↓
┌────────────────────┬────────────────────────┐
│ LocalEmailProvider │ ProductionEmailProvider │
│ (outbox capture)   │ (configuration only)   │
└────────────────────┴────────────────────────┘
```

`deliver_invitation_email(...)` is the single call site: it builds the message,
hands it to the configured provider, and maps **any** provider error to a
`status="failed"` result. It never raises for a delivery failure, so the caller
can always write the audit record that makes the failure visible.

## 4. Local/test provider

`LocalEmailProvider` is the default and the only fully implemented provider.

* **No network I/O** — it holds no HTTP client, session or socket at all
  (asserted by test).
* **No credentials required.**
* Captures messages into a bounded, process-local outbox
  (`OUTBOX_MAX_MESSAGES = 100`), readable via `captured_emails()` in tests.
* **The outbox is never written to the log.** This is deliberate: a test that
  read the invitation URL from a log line would, in a deployed environment, have
  turned captured tokens into production log lines. The provider logs a count
  only — no token, no recipient, no subject.

## 5. Production provider boundary

Configuration (server-side only, `backend/app/config.py`):

| Setting | Purpose |
| --- | --- |
| `EMAIL_PROVIDER` | Selects the provider. `local` (default) = outbox. Anything else = production boundary. |
| `EMAIL_FROM` | Sender address. |
| `EMAIL_REPLY_TO` | Optional reply address. |
| `EMAIL_BASE_URL` | **Authoritative** origin for invitation links. |
| `EMAIL_PROVIDER_API_KEY` | The vendor credential. **Never** returned through any API, never logged, never in a frontend bundle. |

`ProductionEmailProvider` reads the credential into a private attribute and
**refuses to report success**, because no vendor integration exists in this
phase:

* unconfigured → `EMAIL_PROVIDER_NOT_CONFIGURED`
* configured → `EMAIL_PROVIDER_UNAVAILABLE`

A provider that claimed to have sent an invitation it never sent would be a
delivery-failure bug of the worst kind, so this refusal is the safe default. No
vendor is hard-coded; the configured name is carried through and nothing else.

## 6. Invitation email

`render_invitation_email(...)` produces the subject and body:

```
You're invited to administer:

[Institution Name]

You have been invited as a University Administrator.

Accept the invitation:
[url]

This invitation expires at:
[expiry]

This link can only be used once. The account created by this link is bound to
the email address this invitation was sent to; that address cannot be changed
during setup.

If you did not expect this invitation, you can ignore this email.
```

The body contains **no** password, service credential, database identifier,
token hash or unnecessary personal information — each asserted by test.

## 7. Invitation URL

```
build_invitation_url(token) = f"{settings.email_base_url}/admin-invite/{token}"
```

The origin comes **exclusively** from configuration. A request `Host`,
`X-Forwarded-Host` or `X-Forwarded-Proto` header is never consulted, so an
attacker cannot poison the link a Super Admin or invitee receives. (A spoofed
`Host` is separately rejected by the project's existing `TrustedHostMiddleware`;
the stronger property — that no header can influence the link — is what is
tested.)

## 8. Verification model

No new lifecycle state was introduced. The Phase 7.14 vocabulary
(`invited`/`accepted`/`cancelled`/`expired`) remains the single authority, so
the existing terminal-state trigger stays meaningful.

Delivery and verification are **orthogonal bookkeeping on the same row**:

| Field | Meaning |
| --- | --- |
| `email_verified_at` | The server-authoritative email-ownership fact. |
| `email_delivery_status` | `pending` / `sent` / `failed` — delivery, not lifecycle. |

A database CHECK enforces the invariant directly:

```sql
CHECK (email_verified_at IS NULL
       OR (status = 'accepted' AND accepted_at IS NOT NULL))
```

so a still-pending invitation can never be made to look verified — not by the
application, not by a direct database write. `platform_admin_invitations.status`
is unchanged: there is no `email_verified` lifecycle value, and a test asserts
the migration introduces none.

## 9. Email ownership verification

Exactly how ownership is established:

1. The invitation row stores the invited address.
2. The email is delivered **to that address** (the invitation URL is the only
   thing that travels).
3. On acceptance, the server derives the account address **from the invitation
   row**, never from the request:
   ```python
   email = str(invitation["email"])          # server-derived
   auth_user_id = student_svc._create_auth_account(email, payload.password)
   ```
4. The acceptance request schema has **no `email` field** and is
   `extra="forbid"`, so `{"email": "attacker@example.test"}` is rejected 422
   before any code runs. Same for `email_verified`, `email_verified_at`,
   `institution_id`, `role`, `scope` and `status`.
5. After the atomic claim succeeds, the equality is **asserted explicitly**
   (not merely assumed) and `email_verified_at` is recorded, then audited as
   `institution_admin_invitation_verified`.

Verification is therefore server-authoritative end to end. The acceptance page
displays the address as **informational, non-editable** text and renders the
server's `email_verified` flag; it cannot assert it.

## 10. Resend

```
POST /api/v1/platform/institutions/{institution_id}/admins/invitations/{invitation_id}/resend
```

Strategy — deterministic, **one live token at a time**:

```
existing invitation
    ↓ generate a NEW 384-bit secrets token
    ↓ OVERWRITE token_hash + expires_at in ONE conditional update
      WHERE invitation_id = ? AND status = 'invited'
    ↓ the old URL is now dead, structurally
    ↓ attempt delivery, record + audit the real outcome
```

Overwriting rather than inserting a second row is the whole point: a second row
would leave the previous URL valid and accumulate live tokens for one person.
Here there is exactly one usable URL per invitation at every moment, so a
leaked link is closed by a single resend with no residual access.

* Only a **pending** invitation can be resent. Accepted / cancelled / expired
  → `409 INVITATION_NOT_RESENDABLE`, nothing written, nothing sent.
* An invitation that *looks* pending but has elapsed is persisted as `expired`
  and audited, then refused — resend can never resurrect it.
* Institution binding is verified **before** any write; another tenant's
  invitation is a `404` (not a `403`, which would confirm it exists).
* If the rotation loses a race (row stopped being pending), nothing is sent, so
  no live token exists that nobody knows about.
* The new raw token is returned **once**; only its SHA-256 digest is stored.

The Phase 7.14 lifecycle trigger is **replaced, not weakened**: token rotation
is permitted *only* while the row is pending and not transitioning, and
`institution_id`, `role_name`, `email`, `created_by` and `created_at` remain
immutable for the life of the row.

## 11. Rate limits

Implemented in `backend/app/services/invitation_abuse_controls.py`, reusing the
Phase 7.8 `SlidingWindowRateLimiter` primitive with a **separate instance** so
invitation counters never share a bucket with public-chat counters.
`X-Forwarded-For` is ignored (no trusted-proxy configuration), exactly as in
Phase 7.8.

**Actual shipped defaults**, over a 300-second window:

| Scope | Limit | Window |
| --- | --- | --- |
| inspect — per IP | 60 | 300 s |
| accept — per token | 5 | 300 s |
| accept — per IP | 20 | 300 s |
| resend — per invitation | 3 | 300 s |
| resend — per institution | 10 | 300 s |
| resend — per actor | 20 | 300 s |
| resend — per IP | 5 | 300 s |

Rationale: a legitimate invitee inspects the link once or twice and accepts
once, so five acceptances per token is generous while still making automated
attempts impractical. The per-IP inspection budget is the most generous of the
three because inspection is the enumerable surface. The per-invitation resend
budget of three is what bounds how many live tokens can exist.

The acceptance limiter is keyed on the invitation's **stored SHA-256 digest**,
never the raw token, so no usable credential is held in process memory as a
rate-limit key.

Exceeding a budget returns `429 INVITATION_RATE_LIMITED` with a bounded
`Retry-After`. The body exposes no counter values, table names or internal
limiter state. The frontend treats 429 as **retryable, not terminal** — the
same link still works once the window passes, so the form is never withdrawn.

## 12. Expiry sweep

**Server enforcement (the security boundary):** `claim_invitation` re-checks
`expires_at > now()` inside the same conditional statement that consumes the
token. An expired invitation is refused **even if the sweep has never run**.

**The sweep (cleanup only):** `expire_pending_admin_invitations()` selects
`status = 'invited' AND expires_at <= now()` and transitions those rows.

* **Idempotent** — the candidate query and the transition are both conditional
  on `status = 'invited'`, so a second run finds nothing and reports
  `expired = 0`. Accepted / cancelled / already-expired rows are never selected.
* **Audited** — each transition writes
  `institution_admin_invitation_expired` with no token, hash, password or
  credential.
* **Actor** — the invitation's original issuing Super Admin (`created_by`),
  because `actor_user_id` is a non-nullable FK and the sweep is attributable to
  the invitation that is expiring.
* **Bounded** — page size capped at 200 in the repository, server-side.
* A single failing audit write does not abort the run.

**Scheduling — explicitly not claimed.** This deployment is one Uvicorn process
with no worker or scheduler, so **no background process exists**. The execution
boundary is:

* `POST /api/v1/platform/admin-invitations/expire-sweep` (Super Admin only), for
  local development, tests and manual operation;
* direct service invocation from a test.

Wiring it to cron, a queue worker or a platform scheduler is a **deployment
concern for a later phase**. A test asserts no scheduler was added to
`app/main.py`.

## 13. Delivery-failure handling

Correct sequence:

```
Create invitation  →  commit  →  attempt email  →  record + audit the REAL result
```

No database transaction is held open across the provider call.

When delivery fails:

* **No Auth account is created.**
* **No admin role is granted.**
* **The invitation is not marked accepted** and the token is not consumed.
* The failure is **persisted** as `email_delivery_status = 'failed'`, with an
  attempt counter.
* The failure is **audited** as
  `institution_admin_invitation_email_failed` with `result = 'failed'`.
* The API returns the real outcome: `email_delivery.status = "failed"` plus a
  message directing the operator to resend. A failure is **never** reported as
  success.
* **Controlled retry** = resend, which issues a fresh token (invalidating the
  old one) and re-attempts delivery.

A provider that raises an unexpected exception is also contained: the result is
recorded as failed and the invitation service continues.

## 14. Audit events

**New (Phase 7.15):**

| Event | Meaning |
| --- | --- |
| `institution_admin_invitation_email_sent` | Delivery succeeded. |
| `institution_admin_invitation_email_failed` | Delivery failed; the invitation stays live and resendable. |
| `institution_admin_invitation_resent` | A token was superseded and re-sent. |
| `institution_admin_invitation_verified` | The server established email ownership during acceptance. |

`result` gains `failed` so a delivery outage is representable without overloading
`denied` (which means an authorization refusal).

**Preserved (Phase 7.14), unchanged and never duplicated:**
`institution_admin_invited`, `institution_admin_invitation_accepted`,
`institution_admin_invitation_expired`, `institution_admin_invitation_cancelled`,
`institution_admin_revoked`.

## 15. Audit data safety

Audit `details` never contain a raw token, a token hash, a password, a
service-role key or an email-provider API key. Delivery records store the
provider **name** and a bounded status code only. The email address is stored in
audit details, consistent with the existing Phase 7.13/7.14 model, which
already records the invited email on `institution_admin_invited`.

## 16. Migration

`supabase/migrations/20261001030000_phase_7_15_invitation_delivery_email_verification.sql`

Additive columns on `platform_admin_invitations`, each with a demonstrated
requirement:

| Column | Requirement |
| --- | --- |
| `email_verified_at` | Server-authoritative verification state (§9). |
| `email_delivery_status` | Distinguish "the link exists" from "the email went out". |
| `email_delivery_at` | Triage and retry timing. |
| `email_delivery_attempts` | Abuse observability. |
| `last_sent_at` | When a send last succeeded. |
| `resend_count` | Roster signal that a link was reissued. |

Deliberately **not** added: any message body, subject, recipient list, provider
response, raw token, password or credential column. Also: **no new table**, so
this is not an outbox or a messaging platform — the goal is
`Invitation → Email boundary`, nothing more.

Trigger `phase715_assert_invitation_transition` replaces the Phase 7.14 trigger
with one narrow exception (token rotation while pending) and keeps every other
restriction identical.

The Phase 7.12, 7.13 and 7.14 migrations were **not modified**.

## 17. Tests

| Suite | Result |
| --- | --- |
| Focused Phase 7.15 backend | **87 passed** |
| Physical local-DB validation | **12 passed, 1 skipped** (only one seeded institution, so no cross-tenant row to point at) |
| Full backend | **2372 passed, 15 skipped** |
| Frontend | **58/58 files passed** |
| `npx tsc --noEmit` | clean |
| `npm run build` | clean |
| `git diff --check` | clean |

Coverage: email (local capture, production boundary, content, no
password/credential, configured base URL, Host-header immunity); verification
(server-derived binding, every authority-shaped extra rejected, server-recorded
verification); resend (authorization for all four tenant roles + anonymous,
token supersession, terminal refusal, race loss, cross-tenant 404); rate limits
(each scope, safe 429 bodies, enforcement stopping the Auth primitive); expiry
(refusal without any sweep, sweep idempotency, accepted rows untouched);
delivery failure (no account, no role, auditable, retryable); security (no raw
token persistence, no token or password logging, no service-role exposure, no
cross-tenant acceptance, no escalation, no replay); migration contract.

One Phase 7.14 assertion was adapted, not weakened: with Phase 7.15 recording
additional audit events, `audit.call_args` (last call only) can no longer stand
for "the audit record of this request", so those assertions now check the whole
recorded set — which in the token-safety cases **strengthens** the original
intent. A Phase 7.14 fixture also resets the new limiter around each test, so
the pre-existing lifecycle suite stays order-independent.

## 18. Known limitations

These are real, not hypothetical:

1. **No production email provider is integrated.** The boundary, the
   configuration and the failure handling are complete; the vendor call is not.
   With a production provider configured, every send fails closed and is
   auditable. Local development needs no provider at all.
2. **Delivery is attempted synchronously in the request.** If the process dies
   between the commit and the result write, the row keeps
   `email_delivery_status = 'pending'`. This is honest and recoverable by a
   resend, but it is not transactional email delivery. A durable outbox is
   deliberately out of scope for this phase.
3. **No expiry scheduler runs.** The sweep is a manual/service-call boundary;
   production scheduling is unbuilt.
4. **Rate limits are process-local.** They reset on restart and are per worker,
   so horizontally scaling the backend requires a shared store or edge limiter.
   The attempt/resend counters on the row survive restarts, but they are
   advisory and are never used as a security decision.
5. **Delivery counters are read-modify-write**, so concurrent sends can
   undercount. Acceptable for observability; every *security* decision remains a
   single conditional statement.
6. **Email ownership verification is invitation-delivery based.** It proves the
   invitee controlled the address the invitation was sent to, because that
   address is the only one the account can be created with. It is not an SMTP
   challenge/response confirmation, and GoTrue email confirmation is not enabled
   for these accounts.
7. **Resend is offered for expired invitations but not cancelled ones** — a
   deliberate choice, since reissuing a cancelled invitation would undo an
   explicit operator decision.

## 19. Remote safety

All validation used the guarded local stack through
`scripts/validation/invoke_local_supabase.ps1`, which verifies the Docker
context and always passes `--local`. `supabase db push --linked` was **never**
executed. No remote database, Auth instance, email provider, user, institution,
invitation or audit record was touched.

## 20. Recommended next phase

**Phase 7.16 — Production Email Provider & Delivery Reliability.**

1. Integrate one approved production provider behind the existing
   `EmailDeliveryProvider` protocol (no change to the invitation service).
2. Replace synchronous delivery with a durable outbox + worker so delivery
   survives a process restart and is retried with backoff.
3. Add the expiry sweep to a real scheduler (cron / worker) so
   `POST .../expire-sweep` stops being a manual step.
4. Move the rate limiter to a shared store before scaling the backend
   horizontally.
5. Add delivery telemetry (sent / failed / bounced) to the platform audit view.

Each of these is additive to the boundary this phase established; none requires
reworking the invitation authorization model.