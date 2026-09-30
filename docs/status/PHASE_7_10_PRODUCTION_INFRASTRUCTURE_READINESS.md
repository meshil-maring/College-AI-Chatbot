# Phase 7.10 — Production Infrastructure & Remote Reconciliation Readiness

Date: 2026-09-30  
Phase status: **BLOCKED**  
Environment classification: **UNKNOWN**  
Remote reconciliation: **BLOCKED**

## 1. Executive status

The application code and the reconstructed local migration chain are in a
strong locally validated state, but the production environment is not defined
well enough to deploy or reconcile safely. The linked Supabase project is
reachable and was inspected read-only. It is not identified as development,
staging, or production. It has no available physical backup, PITR is disabled,
and no isolated restore has been verified.

The local and remote migration ledgers also diverge in a way that is not a
normal set of pending forward migrations. Twelve of the sixteen local versions
match the remote ledger. Phase 6.11, Phase 7.2, and Phase 7.4 are genuinely
pending, but the newly reconstructed baseline is also local-only while its
principal objects already exist remotely. Applying that baseline normally
would attempt to create existing objects; simply marking it applied would be a
ledger mutation without proven historical equivalence. This divergence must be
understood and resolved through a separately authorized reconciliation plan.

Production hosting, hostnames, TLS termination, SPA rewrites, managed secrets,
monitoring/alerts, and application rollback are not selected or verified. The
public-chat code passes focused tests and production build checks, but its
required remote visibility column and retrieval RPC do not exist.

```text
PHASE_STATUS = BLOCKED
ENVIRONMENT_CLASSIFICATION = UNKNOWN
REMOTE_RECONCILIATION = BLOCKED
TLS_STATUS = NOT_CONFIGURED
```

## 2. Assessment scope and evidence

This phase used repository inspection plus these read-only checks:

- `supabase migration list --linked` — remote ledger reachable; 12 matching,
  4 local-only versions.
- `supabase db dump --linked --schema public` — schema-only inspection written
  to ignored local `supabase/.temp`; no remote write.
- `supabase backups list --project-ref <linked-ref>` — region,
  WAL-G/PITR, and physical-backup inventory only.
- `npm.cmd run build` — PASS; 97 modules transformed.
- `node scripts/verify_frontend_build_security.mjs` — PASS; four generated
  files scanned, only `VITE_API_BASE_URL` allowed, no obvious credential or
  localhost pattern found.
- Focused backend Phase 7.3–7.5/7.8/7.9 tests — PASS; 96 tests.
- Focused frontend route/public-chat tests — PASS; 25 tests in three files.

The earlier Phase 7.9.12 gate provides the local database evidence: two fresh
local resets applied all 16 migrations, produced a complete ordered ledger, and
verified Phase 6.11, Phase 7.2, Phase 7.4, vector, and HNSW objects. This phase
did not repeat those destructive local resets because no migration source has
changed since that gate.

## 3. Production architecture inventory

### Frontend

| Item | Observed state |
| --- | --- |
| Technology | React 19 / TypeScript / Vite static bundle |
| Hosting provider | **UNKNOWN** |
| Production hostname | **UNKNOWN** |
| Preview hostname | **UNKNOWN** |
| Deployment method | **UNKNOWN**; no host manifest, container, or CI/CD deployment workflow found |
| SPA rewrite | **MISSING**; repository has no host rewrite configuration |
| HTTPS | **UNKNOWN / NOT_CONFIGURED** |
| Environment variables | Only public `VITE_API_BASE_URL`; default `/api` |

### Backend

| Item | Observed state |
| --- | --- |
| Technology | FastAPI / Uvicorn / Python >=3.13 |
| Hosting provider | **UNKNOWN** |
| Production hostname | **UNKNOWN** |
| API hostname | **UNKNOWN** |
| Deployment method | No platform service definition; packaged command is `uv run start` |
| Process model | Code enforces one Uvicorn worker in the packaged start path |
| Binding | `0.0.0.0:8000`; dynamic platform port is not supported by current start code |
| HTTPS | Application assumes an external TLS terminator; none selected |
| Environment variables | Typed settings plus fail-fast non-local validation; production values/store **UNKNOWN** |
| Health | `/health` is liveness; `/ready` performs a bounded database read and returns safe 503 |

### Database and Auth

| Item | Observed state |
| --- | --- |
| Provider/project | Supabase project `College AI Chatbot`, ref `rjnfmjcvkfotneswpygr` |
| Environment class | **UNKNOWN**; remote hosting does not prove production |
| Region | `ap-southeast-2` (current backup API and pooler metadata) |
| PostgreSQL | Linked metadata reports PostgreSQL 17.6.1.166 |
| Migration state | 12/16 local versions match; reconstructed baseline plus 6.11, 7.2, 7.4 absent from remote ledger |
| Extensions | `vector` is confirmed usable by the remote 1536-vector column and HNSW index; other production extension inventory **UNKNOWN** |
| Auth configuration | Application expects Supabase email/password Auth and JWKS; current remote provider, redirect, email, MFA, password, and rate-limit settings **UNKNOWN** |

`supabase/config.toml` is local-development configuration. Its local Auth URLs
and policies are not evidence of the remote project's configuration.

### Storage

| Item | Observed state |
| --- | --- |
| Provider | Cloudflare R2 integration exists |
| Production account/bucket | **UNKNOWN** |
| Credentials | Backend-only settings exist; production secret-store installation **UNKNOWN** |
| Access model | Server-side S3 API operations only; no public URL/presigned URL path found. Actual bucket public/private setting is **UNKNOWN** |
| Connectivity | PASS was last recorded in Phase 7.9.1; not evidence of production ownership or recovery/versioning |

### AI provider

| Item | Observed state |
| --- | --- |
| Provider | OpenRouter |
| Key | Backend-only setting; production key/store **UNKNOWN** |
| Generation model default | `openai/gpt-4o-mini` |
| Embedding model/default dimensions | `qwen/qwen3-embedding-8b`, 1536 |
| Request controls | Explicit embedding and public generation timeouts; public output cap 800 tokens |
| Budget/cost controls | **MISSING** durable usage budget and billing enforcement; provider/account spend controls **UNKNOWN** |

## 4. Environment classification

```text
ENVIRONMENT_CLASSIFICATION = UNKNOWN
```

Evidence establishes that the linked project matches the configured backend
project and is reachable. It does not establish its operational purpose,
data criticality, owner approval, user population, or whether it is a
development, staging, or production target. No separate staging project is
configured. Remote reconciliation is blocked until the owner records the
classification and confirms the linked project reference for that environment.

## 5. Remote read-only database assessment

### LOCAL VALIDATED STATE

- All 16 migration files applied successfully in two fresh local resets.
- Local ledger contained all 16 versions in order with no duplicates or gaps.
- Phase 6.11 notification table, trigger, constraints, and four indexes passed.
- Phase 7.2 visibility column/check/index and retrieval RPC passed.
- Phase 7.4 hardened RPC replacement passed, including 1536-dimension and
  completed-processing requirements.
- RPC execution was verified for `postgres` and `service_role`, not `PUBLIC`,
  `anon`, or `authenticated`.
- Vector extension and `chunk_embeddings_embedding_hnsw_idx` passed.

### REMOTE OBSERVED STATE

| Check | Current result |
| --- | --- |
| Reachability | **PASS** — ledger, schema dump, and backup API succeeded |
| Migration history | **DIVERGED** — 12 matches and 4 local-only versions |
| Phase 6.11 | **NOT APPLIED**; notification table/indexes absent |
| Phase 7.2 | **NOT APPLIED** |
| Phase 7.4 | **NOT APPLIED** |
| `knowledge_sources.visibility` | **MISSING** |
| `search_public_knowledge_chunks` | **MISSING** |
| `idx_knowledge_sources_public_policy` | **MISSING** |
| Existing vector index | **AVAILABLE** — HNSW index present |
| Public-schema RLS policies | **MISSING** — no `CREATE POLICY` or row-level-security enablement found in the schema dump |
| Existing scoped vector RPC | **AVAILABLE** — `search_similar_chunks`, revoked from PUBLIC and granted to `service_role` |

The local 16-migration chain itself does not introduce table RLS policies. Its
security model is backend-only access with table/function grants and explicit
service-role-only RPC execution. Therefore there is no omitted Phase 7 RLS
object to apply, but there is also no basis to claim RLS defense-in-depth for
the public schema. Effective direct-role privileges and the lack of RLS require
an explicit production security review before deployment.

The schema dump confirms the missing Phase 7 objects independently of the
ledger. It also confirms that much of the reconstructed baseline already exists
remotely, which is why the missing baseline ledger record cannot be treated as
an ordinary pending migration.

## 6. Migration reconciliation matrix

`APPLIED` in the Local column means applied and verified in the fresh local
reset ledger. `ABSENT` in Remote refers to the migration ledger, with schema
observations called out where material.

| Migration | Local | Remote | Status |
| --- | --- | --- | --- |
| Baseline — `20250717000000` reconstructed pre-3.6 | APPLIED | ABSENT | **DIVERGED** — corresponding schema largely exists; unsafe to apply or mark without provenance review |
| Phase 3.6 — `20250718000000` embeddings | APPLIED | APPLIED | MATCH |
| Phase 3.7.1 — `20260905000000` vector index | APPLIED | APPLIED | MATCH; HNSW observed |
| Phase 3.7.2 — `20260905000001` similarity RPC | APPLIED | APPLIED | MATCH; RPC observed |
| Phase 3.8 — `20260905000002` metadata filtering | APPLIED | APPLIED | MATCH |
| Admin-1 — `20260909000000` | APPLIED | APPLIED | MATCH |
| Admin-2 extracted text — `20260909000001` | APPLIED | APPLIED | MATCH |
| Admin-2 FAQ published — `20260909000002` | APPLIED | APPLIED | MATCH |
| Admin-2 notice published — `20260909000003` | APPLIED | APPLIED | MATCH |
| Phase 6.2 — `20260912000000` | APPLIED | APPLIED | MATCH |
| Phase 6.7 — `20260913000000` attendance | APPLIED | APPLIED | MATCH |
| Phase 6.8 — `20260913010000` results | APPLIED | APPLIED | MATCH |
| Phase 6.11 — `20260914000000` notifications | APPLIED | ABSENT | PENDING; schema objects absent |
| Phase 6.13 — `20260915000000` tenancy | APPLIED | APPLIED | MATCH, but remote ledger contains this later version before missing 6.11 |
| Phase 7.2 — `20260928000000` public policy | APPLIED | ABSENT | PENDING; visibility/index/RPC absent |
| Phase 7.4 — `20260928010000` RAG hardening | APPLIED | ABSENT | PENDING; hardened RPC absent |

```text
REMOTE_RECONCILIATION = BLOCKED
```

Normal migration tooling is not currently safe. A future approved plan must
first prove how the existing remote baseline schema was created and whether it
is equivalent to the reconstructed baseline. Do not apply the baseline over
existing objects, edit the ledger manually, or use migration repair merely to
silence the divergence. Once equivalence and recovery are proven, review the
exact supported reconciliation operation and its dry run before applying the
three genuinely pending migrations in timestamp order.

## 7. Backup and recovery assessment

Current read-only provider response:

```text
region: ap-southeast-2
walg_enabled: true
pitr_enabled: false
available physical backups: 0
```

### Backup

| Capability | Status | Evidence/qualification |
| --- | --- | --- |
| Automated restorable backup | **NOT AVAILABLE / NOT VERIFIED** | WAL-G indicator alone is not a restore point; provider returned no physical backups |
| Retention period | **UNKNOWN** | No backup exists and no policy evidence was available |
| Logical backup | **POSSIBLE, NOT ESTABLISHED** | CLI can dump schema/data; only a schema-only assessment dump was made, not a production backup |
| Physical backup | **NOT AVAILABLE** | Zero returned |
| PITR | **NOT AVAILABLE** | Disabled |

### Restore

| Capability | Status |
| --- | --- |
| Restore procedure documented | **PARTIAL** — safety principles exist, no provider-specific executable runbook |
| Restore tested | **NO** |
| Isolated restore environment | **NOT AVAILABLE / UNKNOWN** |
| Recovery time measured | **NO** |
| Recovery point measured | **NO** |

```text
RPO = UNKNOWN
RTO = UNKNOWN
```

Before migration, establish either a supported provider backup/PITR capability
or a complete encrypted logical/physical backup procedure, then restore into an
isolated compatible project and verify data, schema, extensions, Auth-related
relationships, functions, grants, and application connectivity. A dump command
existing is not evidence of recoverability.

## 8. Production migration safety policy

No remote migration may be authorized until every gate below is evidenced:

1. Classify the target environment and confirm its owner and project reference.
2. Produce a current, protected, restorable backup or supported PITR point.
3. Pass an isolated restore exercise and record RPO/RTO observations.
4. Review the exact migration diff, data transformations, locks, and runtime impact.
5. Inspect the remote schema, extensions, grants, RLS posture, indexes, and functions.
6. Verify local/remote ledger provenance and resolve every divergence without ad-hoc ledger editing.
7. Approve a failure/rollback plan, including schema compatibility and forward-fix criteria.
8. Obtain explicit human authorization for the named target and change window.

After those gates, require a non-applying CLI dry run, preserve sanitized
output, and have the operator re-confirm the target immediately before the
authorized command. Stop on the first failure; do not continue later files or
rerun a partly applied migration blindly.

## 9. Frontend deployment readiness

| Check | Status | Evidence / remaining requirement |
| --- | --- | --- |
| API base URL | **AVAILABLE** | `VITE_API_BASE_URL`, default `/api`; suitable for same-origin routing |
| Public chat URL | **AVAILABLE** | `/public-chat/{institution_code}` is parsed, decoded, normalized, and validated client-side |
| Institution routing | **AVAILABLE** | Codes allow uppercase alphanumeric, `_`, `-`, max 32 after normalization |
| SPA fallback | **MISSING** | Host must return `index.html` for non-file routes and exclude `/api/*` |
| HTTPS | **MISSING / UNKNOWN** | No frontend host selected |
| CORS interaction | **CONDITIONAL** | No backend CORS middleware; current design requires same-origin `/api` routing |
| Environment handling | **AVAILABLE** | Only one allow-listed public build variable |
| Localhost in bundle | **PASS** | Current generated production bundle scan found none |
| Secrets in bundle | **PASS (static scan)** | No obvious secret pattern; scan is not a substitute for deployment inspection |
| Production build | **PASS** | TypeScript + Vite, 97 modules |

`/public-chat/{institution_code}` works after the SPA has loaded, but direct
navigation and refresh require hosting fallback. `/login` and `/register` are
not distinct client-router routes: all non-public paths currently fall through
to the same Auth gate. With a fallback they load the application, but `/register`
does not directly select registration. If stable route-specific login/register
behavior is a deployment requirement, implement and test explicit routing.

## 10. Backend deployment readiness

| Check | Status | Evidence / limitation |
| --- | --- | --- |
| FastAPI startup | **AVAILABLE** | Import-time deployment configuration validation |
| Liveness | **AVAILABLE** | `/health`; process/config liveness only |
| Readiness | **AVAILABLE** | `/ready`; bounded Supabase table read, safe 503 |
| Worker/process | **AVAILABLE FOR ONE INSTANCE** | Packaged start fixes `workers=1` |
| Host binding | **PARTIAL** | `0.0.0.0:8000`; no dynamic `PORT` support |
| Trusted hosts | **AVAILABLE, NOT CONFIGURED** | Exact `ALLOWED_HOSTS` required; wildcard rejected in deployment |
| Trusted proxy | **NOT CONFIGURED** | `proxy_headers=False`; forwarded client headers deliberately ignored |
| CORS | **MISSING BY DESIGN** | Safe only for the intended same-origin topology |
| HTTPS | **EXTERNAL / NOT CONFIGURED** | TLS expected at platform/proxy |
| Logging | **PARTIAL** | Structured event-like application logs; no aggregation, correlation platform, metrics, or alerts |
| Exception handling | **AVAILABLE** | Generic safe 500 envelope; internal exception logged server-side |
| Startup validation | **AVAILABLE** | Non-local startup fails on missing core provider settings, DEBUG, dev mode, hosts, or provider mismatch |

The current safe public deployment model is exactly:

```text
1 worker / 1 instance
```

The packaged command enforces one worker but cannot prevent a hosting platform
from starting multiple replicas. Platform replica count must also be fixed to
one. Multiple workers/instances are blocked until rate and concurrency state is
distributed and client identity is derived through a reviewed trusted-proxy or
edge design.

## 11. TLS/HTTPS readiness

| Item | Status |
| --- | --- |
| TLS terminator | **UNKNOWN** |
| Production hostname | **UNKNOWN** |
| Certificate issuance/renewal | **UNKNOWN** |
| HTTP to HTTPS redirect | **MISSING / UNKNOWN** |
| Backend HSTS | **CODE AVAILABLE** in non-local mode, but unverified at a real HTTPS origin |
| Frontend HSTS/security headers | **MISSING / HOST RESPONSIBILITY** |
| Proxy headers | Disabled; no trusted proxy chain defined |
| Secure cookies | Application does not define its own session cookie; browser token-storage and Supabase Auth deployment behavior require live review |

```text
TLS_STATUS = NOT_CONFIGURED
```

Do not enable forwarded-header trust until the exact terminating proxy, trusted
addresses, and hop behavior are documented and tested. HSTS must only be relied
on after HTTPS and redirect behavior are verified at the public origin.

## 12. SPA routing readiness

The preferred topology remains one HTTPS origin:

```text
/api/*                         -> FastAPI
/assets/*                      -> generated static assets
/public-chat/{institution_code}-> index.html (SPA fallback)
/login                         -> index.html (currently renders generic Auth gate)
/register                      -> index.html (currently renders generic Auth gate)
```

No host is selected and no rewrite configuration exists, so direct-navigation
readiness is **MISSING**. The eventual host must ensure API paths never fall
through to `index.html`, then test direct navigation and refresh for all three
routes. A Vite preview/dev fallback is not proof of production-host behavior.

## 13. Monitoring and alerting assessment

| Surface | Availability | Present evidence | Missing production capability |
| --- | --- | --- | --- |
| Backend availability | PARTIAL | `/health`, `/ready`, host-consumable logs | External uptime check and alerts |
| HTTP 5xx/latency/timeouts | PARTIAL | status/duration logs on public chat; safe handlers | Central metrics, percentiles, thresholds, alerts |
| 429/408/413/503 | PARTIAL | safe responses and some abuse-event logging | Aggregation, dashboards, saturation alerts |
| Provider failures | PARTIAL | normalized failures/logging | Alert policy and provider health dashboard |
| Database | UNKNOWN | Supabase is reachable | Provider dashboard ownership; connection/query/storage/CPU/memory alerts |
| Migration failures | MISSING | Operator can retain CLI output manually | Change-event collection and alert/runbook integration |
| OpenRouter latency/failures | PARTIAL | bounded calls and safe failures | Metrics/alerts, token/cost dashboard |
| AI usage/cost | MISSING | No durable portable usage ledger | Account budget, spend alerts, per-tenant quota/billing |
| Public abuse/concurrency | PARTIAL | local rejection events | Central counts, trends, distributed saturation view |
| Embedding/generation/retrieval failures | PARTIAL | safe errors and local logs | Central classification, SLOs, alerts |

Overall monitoring status: **PARTIAL at code level, MISSING operationally**.
No monitoring platform, exporter, dashboard, log sink, or alert definition is
present. Production should at minimum alert on unavailability, readiness
failure, sustained 5xx, 429/503 spikes, provider failures, database exhaustion,
and process restart/resource pressure without collecting questions, answers,
tokens, or private document content.

## 14. Production secrets assessment

Required backend secrets/configuration include Supabase URL, publishable key,
server secret/service-role key, JWKS URL, OpenRouter API key, R2 endpoint/access
key/secret/bucket, and direct database credentials only if a future deployment
uses them. The frontend requires only the public API base URL.

| Check | Status |
| --- | --- |
| Real `.env` tracked | **NO**; repository and component ignore rules cover local `.env` files |
| Supabase temp credentials tracked | **NO**; `supabase/.temp` ignored |
| Frontend secret variables | **NONE EXPECTED**; source allow-list contains only `VITE_API_BASE_URL` |
| Generated bundle obvious secrets | **PASS** current static scan |
| Backend-only secret boundary | **AVAILABLE IN CODE** |
| Production managed secret store | **UNKNOWN / NOT SELECTED** |
| Rotation procedure | **MISSING** |

A path-only high-confidence tracked scan found detector strings, fixtures, and
documentation in tests/scripts/docs, not a confirmed committed credential. No
secret values were printed during this assessment. Before deployment, perform
a reviewed repository-history and artifact scan, install secrets in the chosen
host's managed store, record owners and rotation/revocation steps, and rotate
any credential suspected of prior exposure.

## 15. Public chat production assessment

### API and isolation

- Strict request accepts only `institution_code` and `message`; extra fields
  are rejected. Message contract is 1–4,000 normalized characters.
- Public response is projected to `answer`, `status`, and safe source
  `title`/`section`/`quote`; no IDs, provider/model, token usage, diagnostics,
  authorization metadata, or internal retrieval controls are returned.
- Institution code resolves server-side. Retrieval and a second provenance
  check enforce institution, public visibility, source type, lifecycle,
  effective dates, document/version/run state, and embedding metadata.
- Personal/private-record questions are rejected before public generation.
- Remote enforcement is currently **NOT RUNNABLE** because the visibility
  column and public retrieval RPC are absent.

### RAG and generation

- Retrieval top-K is server-owned and capped at 4.
- Individual context chunks are capped at 4,000 characters and total context
  at 12,000; oversized content is excluded rather than altered.
- Embedding and public generation calls use explicit 30-second defaults.
- Output is capped at 800 tokens and 12,000 projected characters.
- Grounding instructions treat retrieved text as untrusted content; answer and
  citation projection is validated.
- Empty verified context bypasses provider generation and returns insufficient
  context.

### Abuse controls

- 8,192-byte public body cap and five-second body receive timeout.
- Sliding-window direct-peer, institution, and global limits.
- Global and per-institution concurrency gates with safe 503 behavior.
- Safe 408/413/429/5xx errors and message-free abuse logs.
- Browser uses a 35-second abort timeout and does not automatically retry.

### Remaining production limitations

- Rate and concurrency controls are process-local.
- No distributed limiter or shared concurrency accounting.
- No durable usage/token/cost budget.
- No CAPTCHA or bot scoring.
- No billing/quota enforcement.
- No trusted proxy identity; behind a proxy, clients conservatively share the
  proxy's direct-peer bucket.
- No horizontal scaling until distributed controls and trusted identity exist.
- No remotely deployed Phase 7 policy/RPC, so public RAG is not production-ready.

Public-chat code readiness is **PARTIAL**; deployed end-to-end readiness is
**BLOCKED**.

## 16. Rollback strategy

### Application

| Area | Status | Meaning |
| --- | --- | --- |
| Frontend rollback | **NOT VERIFIED** | No host or immutable artifact retention/rollback control selected |
| Backend rollback | **NOT VERIFIED** | No host, release artifact, traffic switch, or prior-release command selected |

The selected platform must retain immutable frontend/backend artifacts, support
redeploying the previous known-good pair, and verify that the older application
is compatible with the current database schema before rollback.

### Database

| Area | Status | Meaning |
| --- | --- | --- |
| Down migrations | **NOT AVAILABLE** | Pending migrations have no reviewed down chain |
| Backup restore | **NOT AVAILABLE / NOT VERIFIED** | PITR off, zero physical backups, no isolated restore |
| Forward fix | **SUPPORTED AS STRATEGY, NOT TESTED** | Preferred after investigation when data/schema can be preserved |

Application rollback never reverses database state. Phase 7.2 performs a data
classification backfill, so ad-hoc reverse SQL is especially unsafe. On
failure, stop, preserve sanitized evidence, assess partial state against the
verified recovery point, then restore through the approved mechanism or issue
a separately reviewed forward migration.

### AI

| Area | Status | Meaning |
| --- | --- | --- |
| Model change | **CONFIGURABLE, NOT A VERIFIED FAILOVER** | One configured OpenRouter model |
| Provider fallback | **NOT AVAILABLE** | Only OpenRouter is supported by startup validation |
| Safe degradation | **PARTIAL** | Timeouts/provider errors are safe; empty context bypasses generation |

## 17. Production readiness matrix

| Area | Status | Evidence | Blocker |
| --- | --- | --- | --- |
| Environment | BLOCKED | Linked target reachable | Classification/owner unknown |
| Supabase | PARTIAL | Project/region/schema reachable | Auth settings unknown; public RLS absent; Phase 7 objects absent |
| Backup | BLOCKED | WAL-G true | PITR off; zero physical backups; retention unknown |
| Restore | BLOCKED | Safety outline only | No isolated restore or measured RPO/RTO |
| Migrations | BLOCKED | Local 16 pass; remote 12 match | Baseline ledger/schema divergence plus three pending versions |
| Frontend hosting | BLOCKED | Production build passes | Provider/hostname/deploy config unknown |
| Backend hosting | BLOCKED | Packaged one-worker start | Provider/service/hostname/dynamic-port policy unknown |
| HTTPS | BLOCKED | Backend can emit HSTS | No terminator, cert, redirect, or hostname |
| SPA routing | BLOCKED | Routes handled after app load | No production fallback; login/register not explicit routes |
| Secrets | BLOCKED | Ignore rules and bundle scan pass | No managed production store or rotation procedure |
| Monitoring | BLOCKED | Health/readiness and local logs | No platform, aggregation, metrics, alerts, SLOs |
| Rollback | BLOCKED | Strategy principles documented | No host rollback; no restorable DB recovery path |
| Public chat | BLOCKED | Focused tests/build pass | Required remote visibility/RPC absent; no deployed smoke |
| Abuse protection | PARTIAL | Local rate/body/concurrency controls pass | Single process only; no trusted proxy/distributed budget |

## 18. Explicit blockers

1. Linked Supabase environment classification and owner authorization are missing.
2. PITR is disabled, physical backups are zero, and restore is untested.
3. The reconstructed baseline is missing from the remote ledger while its
   schema largely exists; historical equivalence is not established.
4. Phase 6.11, Phase 7.2, and Phase 7.4 are absent remotely.
5. Public visibility, policy index, and public retrieval RPC are absent remotely.
6. Remote Auth configuration and effective direct-role/RLS posture are not approved.
7. Frontend/backend hosts, production hostnames, DNS, TLS, and SPA/API routing are unselected.
8. Production secrets store and rotation procedure are missing.
9. Operational monitoring, alerts, usage/cost controls, and SLOs are missing.
10. Application rollback and database restore are not verified.
11. Public abuse controls permit only one worker and one instance.
12. No deployed public-chat end-to-end smoke or eligibility matrix can run yet.

## 19. Required next actions

1. Have the project owner classify the linked Supabase project and name the
   intended development, staging, and production projects.
2. Establish a supported backup/PITR plan and pass a documented isolated
   restore exercise; record observed RPO/RTO and retention.
3. Perform a dedicated baseline provenance/reconciliation review: compare the
   reconstructed baseline object-by-object with the remote pre-3.6 schema and
   choose a supported, explicitly authorized ledger strategy. Do not mutate the
   ledger during assessment.
4. After recovery and ledger gates pass, review a non-applying migration dry
   run for the exact target and all pending versions. Obtain change-window
   authorization before any application.
5. Select one frontend/backend hosting topology. Prefer same-origin HTTPS with
   `/api/*` routed to the one-instance FastAPI service and SPA fallback for
   frontend routes.
6. Configure exact hostnames, TLS/cert renewal, redirect behavior, frontend
   security headers, `ALLOWED_HOSTS`, and production flags; keep proxy-header
   trust disabled until the proxy chain is verified.
7. Install backend secrets in a managed store and document rotation/revocation.
8. Configure availability, error, latency, saturation, database, provider, and
   cost monitoring with alerts and privacy-safe logging.
9. Verify immutable application rollback and provider/database recovery runbooks.
10. After authorized reconciliation and deployment, run schema/grant checks,
    the public eligibility matrix, direct-route browser checks, security-header
    inspection, and one safe public RAG smoke test.

Recommended next phase:

```text
PHASE 7.11 — Environment Classification, Backup/Restore Proof,
and Baseline Reconciliation Design (read-only until separately authorized)
```

## 20. Remote modification statement

```text
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote data modified: NO
Production deployment performed: NO
DNS modified: NO
```

This phase performed read-only remote ledger, schema, and backup-metadata
inspection only. The schema dump was written to an ignored local temporary
file. No migration push, migration repair, SQL mutation, Auth operation, data
write, provider feature change, deployment, DNS change, or secret change was
performed.
