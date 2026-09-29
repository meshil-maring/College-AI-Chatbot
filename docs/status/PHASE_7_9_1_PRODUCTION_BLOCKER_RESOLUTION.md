# Phase 7.9.1 — Production Blocker Resolution & Remote Verification

Date: 2026-09-29  
Status: **INCOMPLETE — migration safety gate failed; remote database unchanged**

## 1. Objective and safety outcome

This phase re-opened the blockers from Phase 7.9, beginning with the remote
Supabase migration/RPC dependency. The linked Supabase project was confirmed to
match the backend's configured project without printing its identifier. All
database actions in this phase were read-only.

The required pre-migration backup check returned:

```text
walg_enabled: true
pitr_enabled: false
available physical backups: 0
```

There is no verified restore point. Per the Phase 7.9.1 critical safety rule,
the migration chain was **not applied**, no migration ledger entry was edited,
and no production data was changed manually.

```text
REMOTE BACKUP SAFETY: VERIFIED UNSAFE FOR MIGRATION
BACKUP/PITR: NOT AVAILABLE / NOT VERIFIED AS RESTORABLE
```

## 2. Migration state and target

`supabase/.temp/project-ref` exists, and its linked project reference matches
the project reference in the backend's configured `SUPABASE_URL`. The read-only
remote ledger reports:

| Migration | Remote state |
| --- | --- |
| `20260914000000_phase_6_11_student_notifications.sql` | NOT APPLIED |
| `20260928000000_phase_7_2_public_knowledge_policy.sql` | NOT APPLIED |
| `20260928010000_phase_7_4_public_rag_hardening.sql` | NOT APPLIED |

All earlier vector/embedding migrations required by Phase 7 and the Phase 6.13
tenancy migration are applied. The pending Phase 6.11 notification migration is
chronologically earlier than Phase 7. A normal project migration push would
therefore apply three pending migrations, not only the two Phase 7 files. No
dependency was skipped or manually marked applied.

```text
Phase 7.2 migration: NOT APPLIED
Phase 7.4 migration: NOT APPLIED
```

## 3. Migration review

### Phase 6.11 pending predecessor

Creates the student-notification table, indexes, tenant-guard function/trigger,
and service-role grants. It does not drop or delete data, but it is an additional
schema change outside the two requested Phase 7 migrations and must be included
in backup/change review before using the established ordered migration mechanism.

### Phase 7.2

- Adds non-null `knowledge_sources.visibility` with fail-closed `restricted`
  default and checked `public|authenticated|restricted` vocabulary.
- Drops/recreates only the visibility constraint.
- Backfills only already-published FAQ/notice/handbook sources to `public`.
- Adds the institution/visibility/lifecycle policy index.
- Creates the tenant-, lifecycle-, effective-date-, version-, processing-, and
  embedding-state-aware public vector RPC.
- Revokes function execution from `PUBLIC`, `anon`, and `authenticated`; grants
  execution only to `service_role`.

There is no table drop or row deletion. The backfill intentionally changes
existing source rows and is the reason a verified recovery point is required.
Re-running the file later as an ad-hoc repair could re-publicize qualifying rows;
it must be applied exactly once through the ordered migration ledger.

### Phase 7.4

Replaces the same RPC to require `match_count BETWEEN 1 AND 20`, cap the SQL
limit at 20, require `completed_at`, and require 1536-dimensional embedding
metadata while preserving the Phase 7.2 tenant/public/lifecycle/date/state
predicates and service-role-only grant. It contains no destructive data change.

## 4. Remote schema and RPC evidence

The value-free read-only infrastructure check returned:

```text
SUPABASE_CONNECTIVITY=PASS
PUBLIC_VISIBILITY_COLUMN=FAIL
PUBLIC_RPC_AVAILABLE=FAIL
R2_CONNECTIVITY=PASS
```

This independently confirms the ledger result: the Phase 7 visibility schema
and `search_public_knowledge_chunks` RPC do not exist remotely. Because the
function is absent, its signature, return shape, live grants, tenant predicate,
eligibility matrix, and live public retrieval cannot be verified or passed.

No `INSERT`, `UPDATE`, `DELETE`, fixture creation, arbitrary SQL, or ledger
repair was performed. The controlled eligibility matrix was not attempted
against production because creating test records would be unnecessary mutation
and the required schema is absent.

## 5. Remote RAG and public generation

Remote public RAG cannot execute without the RPC. Consequently, a full public
API retrieval-to-OpenRouter smoke request was not made: it would spend an
embedding request only to fail at the known missing database function. The
minimal OpenRouter generation and R2 connectivity checks from Phase 7.9 remain
valid, while the complete real public flow remains blocked.

```text
Remote public retrieval: FAIL
Real public RAG: FAIL
Real public generation flow: FAIL / NOT RUNNABLE
```

## 6. Deployment blockers

Repository inspection again found no Dockerfile, Compose, Render, Fly, Vercel,
Netlify, Nginx, Railway, Cloudflare Workers/Pages, Procfile, or other deployment
definition, and no production deployment hostname. Therefore no platform can be
safely assumed and no platform-specific rewrite/proxy file was invented.

Unresolved external deployment prerequisites are:

- select the actual frontend/backend hosting platform and production hostname;
- configure SPA history fallback for `/public-chat/*` without rewriting assets;
- route same-origin `/api/*` to FastAPI, or explicitly configure a reviewed
  cross-origin topology;
- configure exact production `ALLOWED_HOSTS` without development hosts or `*`;
- verify the real TLS terminator and HTTP-to-HTTPS redirect;
- verify frontend CSP, HSTS, nosniff, referrer, and frame policy at the host;
- identify any proxy hop before enabling proxy-header parsing;
- configure production log aggregation, uptime/error/latency/429/503/provider/
  database monitoring and alerts;
- verify platform artifact rollback and Supabase recovery procedures.

Current safe backend topology remains one worker/process with direct-peer IP
identity and no trusted forwarding headers. CORS remains intentionally absent
for the documented same-origin design.

```text
MONITORING: EXTERNAL DEPLOYMENT PREREQUISITE
TRUSTED PROXY: NOT CONFIGURED
HORIZONTAL ABUSE ENFORCEMENT: NOT AVAILABLE
```

## 7. Production configuration and endpoints

Local tests continue to verify production startup with `DEBUG=false`,
`DEV_TEST_MODE=false`, explicit `ALLOWED_HOSTS`, one worker, reload disabled,
proxy-header trust disabled, `/health` liveness, bounded database `/ready`, API
security headers/HSTS, untrusted-host rejection, and production 404 behavior for
`/docs`, `/redoc`, and `/openapi.json` under the environment-aware docs policy.

The actual production hostname, public URL, and platform secret store do not
exist in repository evidence and remain external. No actual secret was added to
documentation or source.

## 8. Frontend and browser status

The frontend production API base remains same-origin `/api`; the bundle scan
guards against localhost and secret material. Application-level direct routing,
public request projection, safe errors, institution-namespaced localStorage,
refresh restoration, invalid institution, 429/503 handling, and absence of auth
headers/internal controls remain regression-tested.

No deployed URL exists, so actual host SPA fallback, HTTPS/browser headers,
network inspection, refresh against production, deployed logs, and a real
browser public-chat flow remain unverified.

## 9. Regression evidence

```text
Complete backend:
  DEBUG=true uv run pytest -q tests
  2128 passed, 15 skipped, 6 warnings

Phase 7 production-style subset:
  DEBUG=false uv run pytest -q <Phase 7.2, 7.3, 7.4, 7.5, 7.8, 7.9 files>
  110 passed, 1 warning

Frontend first exact attempt:
  npm.cmd run test
  43 files / 321 tests passed; 7 files failed to start because Windows fork
  workers timed out (no assertion failures; exit 1)

Frontend authoritative isolated fallback:
  npm.cmd run test -- --pool=vmThreads --maxWorkers=1
  50 files passed, 431 tests passed

TypeScript:
  npx.cmd tsc --noEmit -p tsconfig.json
  exit 0

Production build:
  npm.cmd run build
  97 modules transformed; passed
```

The worker-start failure is an environment/tooling event already documented in
earlier phases; the isolated full-suite fallback preserves per-file isolation
and passed every test.

## 10. Blocker disposition

| Phase 7.9 blocker | Result |
| --- | --- |
| Target remote project uncertain | RESOLVED — linked target matches backend configuration |
| Backup/PITR unknown | RESOLVED AS NEGATIVE EVIDENCE — PITR off, zero backups; migration blocked |
| Phase 7.2 migration absent | NOT RESOLVED |
| Phase 7.4 migration absent | NOT RESOLVED |
| Public RPC absent | NOT RESOLVED |
| Remote eligibility matrix | NOT RESOLVED / not runnable |
| Real remote RAG/generation flow | NOT RESOLVED / not runnable |
| HTTPS/redirect | NOT RESOLVED — no deployment |
| SPA/API production routing | NOT RESOLVED — no platform selected |
| Production hostname | NOT RESOLVED |
| Frontend security headers | NOT RESOLVED — no deployed response |
| Monitoring/alerts | NOT RESOLVED |
| Platform rollback | NOT RESOLVED |
| Single-process limitation | DOCUMENTED AND ENFORCED locally |
| Trusted proxy | DOCUMENTED AS NOT CONFIGURED; direct peer retained |

## 11. Required next actions

1. Establish and verify a restorable Supabase backup or PITR capability for the
   linked target.
2. Review the full pending ordered chain, including `20260914000000`, then apply
   it through the established Supabase migration command—never ledger repair.
3. Re-run the ledger, visibility-column, RPC existence/signature/grant, schema,
   index, and controlled eligibility-matrix checks.
4. Run one safe remote retrieval and one full public API generation smoke flow.
5. Select the deployment platform/host and verify HTTPS, redirects, SPA/API
   routing, exact allowed hosts, frontend headers, logs, monitoring, and rollback.
6. Run the real production browser flow and negative checks.

## 12. Readiness and final status

```text
Demo readiness: NOT READY
Single-instance production: NOT READY
Horizontal scaling: NOT READY
```

```text
PHASE 7.9.1 STATUS: INCOMPLETE
```

Exact blockers: no restorable remote backup/PITR; three ordered remote
migrations pending; Phase 7 visibility schema and public RPC absent; remote
eligibility/RAG/generation smoke unavailable; and no actual production host,
TLS, SPA/API routing, frontend security policy, monitoring, or rollback evidence.
