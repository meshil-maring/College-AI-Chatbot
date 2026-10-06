# Phase 10 Production Security Audit

Audit date: 2026-10-05  
Scope: FastAPI backend, React/Vite frontend, Supabase/PostgreSQL migrations,
Cloudflare R2 integration, OpenRouter integration, tests, and deployment
configuration present in this repository.

## Executive summary

The application already has meaningful server-side authorization controls:
Supabase JWT signature/audience/expiry validation, server-resolved identities,
institution-scoped role grants, granular permission checks, tenant row guards,
Super Admin isolation, append-only authorization audit records, public-knowledge
provenance checks, and dedicated abuse controls for authentication, invitations,
and public chat.

The pre-change audit nevertheless found one critical API-boundary issue and
several production-hardening gaps. The authenticated chat HTTP contract accepts
internal retrieval fields (including caller-provided chunks and model choice),
allowing a modified client to bypass authoritative retrieval. JWT verification
does not validate the issuer. The base authentication dependency does not reject
an account that was deactivated after its access token was issued. Request-size
limits cover only public chat, uploads are read completely before size and
content checks, and the API has no general application-layer request budget.
CORS is implicitly same-origin but is not configurable as an explicit allowlist.

This document records the repository as found before Phase 10 code changes.
The remediation and verification sections are updated as hardening is applied.

## Architecture and existing controls (pre-change)

### Backend boundary

- FastAPI is the only application API. It uses `TrustedHostMiddleware` and a
  custom security-header middleware. Interactive API docs default off outside
  local/test environments.
- Supabase Auth remains the credential/session authority. The backend verifies
  ES256 access tokens from configured JWKS, requires `sub`, `exp`, and `aud`,
  and requires the `authenticated` audience.
- Application identity, roles, institution scope, and permissions are loaded
  from server-side database rows after JWT verification. Client role/scope
  fields do not participate in authorization.
- Institution APIs use active institution grant resolution plus permission
  maps. Platform APIs use a fresh database check for the active,
  platform-scoped `super_admin` grant on every request.
- Public chat is stateless, resolves the institution from a public code,
  retrieves only published/effective public knowledge, reconstructs canonical
  chunks from repository provenance, bounds context/output, rejects likely
  personal-data questions, and exposes a reduced response projection.
- Process-local sliding-window controls exist for login/recovery/password
  operations, invitation inspect/accept/resend operations, and public chat.
  Public chat also has global/per-institution concurrency gates.
- Unhandled exceptions return a generic error envelope. Validation errors are
  normalized and omit non-serializable validator context.

### Authorization and tenancy

- Admin routes use a fail-closed route-to-permission map; routes absent from the
  map are denied. They also require an active institution role and use tenant
  guards before operating on tenant resources.
- Platform routes use a separate fail-closed permission map and the dedicated
  Super Admin dependency. Super Admin does not implicitly receive tenant data
  access.
- Student self-service routes derive the student identity from the authenticated
  application user and do not accept another student ID.
- Conversation history reads verify ownership and return 404 for foreign IDs.
- Database access uses the Supabase service role from the backend. Migrations
  explicitly withhold public/anon/authenticated access from sensitive tables
  and RPCs. Because service-role access bypasses RLS, application tenant filters
  remain a critical security boundary.
- Privileged admin/platform mutations are recorded in durable audit tables;
  authentication operations have a separate durable security-event table.

### File ingestion and storage

- Ingestion permits PDF, DOCX, and TXT extensions/MIME types, has a configured
  maximum file size, sanitizes the filename used in R2 keys, computes SHA-256,
  and prefixes object keys with institution/source/version identifiers.
- R2 credentials and bucket configuration remain backend-only. The frontend is
  not given R2 credentials or direct object URLs.
- Pre-change limitations: the whole upload is read before the size check;
  extension and client MIME are trusted without signature/container checks;
  ZIP/PDF parser-complexity limits are absent; storage downloads are unbounded;
  CSV upload is also read without an explicit endpoint limit.

### Frontend boundary

- The frontend treats the backend as authoritative for role, tenant, and
  permissions. Route guards are user experience controls only; bearer tokens
  are sent to protected backend endpoints.
- Access and refresh tokens are persisted in `localStorage`; passwords and
  invitation tokens are not persisted. Password-recovery fragment tokens are
  removed from browser history and are not copied to browser storage.
- React rendering is used without `dangerouslySetInnerHTML` in application
  code. The public chat storage layer validates and bounds persisted display
  data and excludes backend/internal identifiers.
- The local Vite proxy produces same-origin `/api` calls. A production CSP is
  documented as required, but no repository-owned production hosting header
  configuration exists pre-change.

### Infrastructure/configuration

- Non-local startup validation requires Supabase, R2, OpenRouter, email, and
  webhook settings; rejects debug mode, wildcard hosts, dev auth mode, capture
  email providers, and invalid email URLs/keys.
- The backend has no explicit CORS middleware. This is safe for the documented
  same-origin deployment but cannot express a separate trusted frontend origin.
- Rate counters are process-local. They reset on restart and are independent per
  worker, so the repository correctly notes that an edge/shared limiter is
  required for horizontally scaled production.
- No reverse-proxy trust configuration is present; direct peer IP is used and
  forwarding headers are ignored, preventing spoofing but collapsing clients
  behind a proxy into a single bucket.
- HTTPS is assumed to terminate upstream. HSTS is added by the application in
  non-local environments.
- Local `.env` is ignored and present in the working tree; no real `.env` or
  local credential fixture is tracked by Git. Values were not read or copied
  into this audit.

## Threat model

| Actor | Important attack paths | Required controls |
| --- | --- | --- |
| Anonymous attacker | Public AI cost exhaustion, registration/recovery spam, invitation enumeration, webhook flooding, malformed/oversized bodies | Edge and app budgets, request caps/timeouts, generic errors, signature/token checks, strict schemas |
| Authenticated student | Other-student IDs, conversation IDOR, tenant override, admin/platform calls, AI prompt/cost abuse | Server-derived identity, ownership checks, institution scope, permissions, AI budgets |
| Faculty | Unassigned sections, other faculty/students, unauthorized attendance/results, cross-tenant knowledge | Section assignment checks, exact permissions, tenant filters, audit |
| Staff | Direct-grant escalation, unauthorized admin actions, cross-tenant records | Non-delegable permission allowlist, institution-bound grants, route policy, audit |
| University Admin | Super Admin/platform escalation, another institution, global role changes | Separate platform role/scope dependency, tenant pinning, non-client-controlled grants |
| Compromised browser/client | Arbitrary bodies/headers/IDs, hidden UI bypass, stored-token theft after XSS | All decisions server-side, narrow contracts, CSP/XSS prevention, short JWT lifetime, rotation/revocation |
| Compromised third party/provider | Malicious AI output, forged webhook, storage object manipulation, provider error leakage | Grounding/provenance validation, HMAC/replay checks, checksums/content validation, safe errors and logging |

## Findings and disposition

| ID | Severity | Pre-change finding | Planned disposition |
| --- | --- | --- | --- |
| P10-01 | Critical | Authenticated chat accepts `retrieved_chunks`, model, and document/run/source filters from the HTTP caller; supplied chunks skip retrieval. | Introduce a narrow external chat request and reconstruct the internal request server-side. |
| P10-02 | High | JWT validates signature/audience/expiry but not issuer; bearer length is not bounded. | Require the configured/derived Supabase issuer and bound bearer input. |
| P10-03 | High | Base `get_current_user` does not fail closed for a freshly deactivated account; some routes only use this base dependency. | Reject non-active application users in the base dependency. |
| P10-04 | High | Only public chat has an early body cap; webhook/JSON/CSV/upload endpoints lack a uniform request-size boundary. | Add route-aware ASGI request-size enforcement and preserve the tighter public cap. |
| P10-05 | High | Upload reads the entire file before checking length and trusts extension/MIME without content checks; archive/parser bombs are not bounded. | Stream with a hard cap, validate signatures/container safety, and bound extraction. |
| P10-06 | Medium | No general API rate budget or authenticated AI budget exists. Existing limiters are process-local and endpoint-specific. | Add coarse application limits and document mandatory edge/shared rules. |
| P10-07 | Medium | CORS is implicit same-origin only and cannot safely allow a separately hosted frontend. | Add an explicit origin allowlist with credentials disabled and production validation. |
| P10-08 | Medium | Cross-user chat continuation returns 403 while history reads return opaque 404. | Normalize foreign conversation IDs to the 404 ownership contract. |
| P10-09 | Medium | Several admin/public request models contain unbounded strings or accept ignored extra fields; some pagination values are plain unbounded integers. | Add strict request schemas, field limits, and query bounds where exposed. |
| P10-10 | Medium | API headers omit cache prevention/CSP; frontend production CSP is not repository-enforced. | Expand API headers and add a same-origin frontend CSP baseline plus hosting guidance. |
| P10-11 | Medium | Provider URLs/R2/Supabase/JWKS relationships are not fully validated in deployment configuration. | Add HTTPS/origin/issuer consistency checks without logging values. |
| P10-12 | Medium | Auth signup exposes raw provider messages; processing records persist raw exception strings. | Replace client-visible/provider-derived and persisted exception text with stable categories. |
| P10-13 | Medium | Access and refresh tokens persist in `localStorage`, increasing impact of frontend XSS. | Retain current session architecture (out of redesign scope), enforce CSP guidance, short access-token lifetime, rotation, and no third-party script policy. |
| P10-14 | Low | Direct peer addressing is spoof-resistant but not proxy-aware; at a reverse proxy all users may share a bucket. | Document trusted-edge requirement; do not trust forwarding headers in app without an explicit proxy contract. |
| P10-15 | Low | Dependency manifests are locked, but no repository CI vulnerability gate is defined. | Run available audits and document repeatable CI commands/remediation policy. |

## CSRF assessment

The application does not use browser cookies for authentication. Protected
operations require a bearer token in the `Authorization` header, and JSON or
multipart authenticated requests trigger CORS preflight when cross-origin.
Classic ambient-cookie CSRF is therefore not applicable to the current design.
Public registration/chat/recovery endpoints are intentionally unauthenticated
and need abuse controls rather than CSRF tokens. Mailgun webhooks use HMAC plus
timestamp/replay reconciliation. If authentication is later moved to cookies,
SameSite/secure/HttpOnly cookies plus origin checks and CSRF tokens must be added
before that change ships.

## Production deployment requirements

The application limiter is defense in depth, not the Internet edge. Production
must implement the following order:

```text
Internet
  -> WAF / gateway shared rate and body limits
  -> TLS termination and canonical host enforcement
  -> application request/body/concurrency controls
  -> authentication
  -> permission + role/scope authorization
  -> tenant/ownership resource check
  -> database, storage, or AI provider
```

Required edge policies and final verification results are recorded below as the
Phase 10 implementation is completed.

## Remediation status

Pending implementation.

## Verification status

Pending implementation and regression testing.
