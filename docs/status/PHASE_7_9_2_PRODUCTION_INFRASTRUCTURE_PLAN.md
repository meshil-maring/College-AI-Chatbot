# Phase 7.9.2 — Production Infrastructure & Recovery Plan

Date: 2026-09-29  
Status: **INCOMPLETE — production platform and recovery mechanism remain unselected/unverified**

## 1. Objective

Establish the infrastructure and recovery path required before safely applying
the pending migrations and deploying the public chatbot. This document records
repository evidence, the target topology shape, recovery requirements, and two
explicit release gates. It does not authorize a cloud-provider choice, paid
service change, remote migration, or deployment.

## 2. Current environment and evidence

- The repository has a Vite/React/TypeScript frontend, FastAPI backend,
  Supabase database/Auth/pgvector, Cloudflare R2 storage, and OpenRouter
  generation/embeddings.
- Repository search found no Dockerfile, Compose file, Render/Fly/Vercel/
  Netlify/Railway/Cloudflare deployment config, Nginx/Caddy config, Procfile,
  GitHub Actions workflow, CI/CD definition, production deployment script, or
  deployment hostname.
- `frontend/vite.config.ts` contains a development-only `/api` proxy to
  localhost. It is not production routing configuration.
- `backend/app/main.py` provides `/health` liveness and `/ready` database
  readiness. `uv run start` binds port 8000, uses one worker, disables reload
  outside local development, and does not trust proxy headers.
- `supabase/config.toml` configures local Supabase development; it is not proof
  of a production project or a backup policy.
- The linked remote Supabase project matches the project's backend URL, but
  repository and provider evidence do not establish whether it is development,
  staging, or production.
- No staging environment is configured.

```text
PRODUCTION PLATFORM: NOT SELECTED
PRODUCTION HOSTNAME/DNS: NOT CONFIGURED
STAGING: NOT CONFIGURED
CURRENT LINKED SUPABASE ENVIRONMENT: NOT CLASSIFIED
```

## 3. Deployment decision record

### Selected topology

No deployable production topology can be selected from repository evidence.
The following is the target shape for a later project/platform decision, not a
claim that it has been deployed:

```text
Internet
  -> selected HTTPS/TLS terminator and DNS
  -> one public application origin
       /public-chat/* -> static React SPA with history fallback
       /api/*         -> FastAPI, one process/worker
                         -> Supabase (database/Auth/pgvector)
                         -> Cloudflare R2 (private objects)
                         -> OpenRouter (embeddings/generation)
```

The code supports same-origin `/api` by default and has no CORS middleware.
Same-origin is therefore the lower-configuration target. This is an
architectural preference, not a selected hosting or DNS decision.

### Component disposition

| Component | Current implementation/evidence | Production decision |
| --- | --- | --- |
| Frontend host | Vite build output; no static host config | TBD |
| Backend host | FastAPI/Uvicorn packaged `start`; no service definition | TBD |
| Database | Linked Supabase project; environment class unknown | Existing project intended only after operator classification |
| Object storage | Cloudflare R2 server-side S3 client | Existing R2 configuration; production account/bucket ownership not documented |
| AI provider | OpenRouter server-side chat and embedding clients | Existing provider; production key/budget ownership to confirm |
| TLS terminator | None identified | TBD |
| DNS | No hostname/domain found | TBD; do not invent a domain |
| Reverse proxy | None identified | TBD; no proxy-header trust |
| Monitoring | Application/process logs only | External monitoring/alerts TBD |

### Same-origin and separate-origin

Target preference is a same-origin public site, for example
`https://<site-domain>/public-chat/COLLEGE001` with API requests at
`https://<site-domain>/api/v1/chat/public`. This keeps browser CORS minimal and
allows a single TLS/routing boundary. The actual domain and platform remain TBD.

A separate frontend/API origin such as `https://<app-domain>` and
`https://<api-domain>` is not configured. It would require explicit CORS
allow-listing, separate DNS/TLS, and independent host/security-header checks.
Do not deploy cross-origin until that topology is chosen and reviewed.

## 4. Frontend deployment plan

- Build with `npm run build`; deploy the contents of `frontend/dist` to the
  selected static host.
- Keep `VITE_API_BASE_URL=/api` for same-origin routing. It is public build
  configuration, not a secret.
- Configure SPA history fallback so `/public-chat/{institution_code}` and
  `/public-chat/COLLEGE001` return `index.html` on direct load and refresh.
- Serve `/assets/*` as the generated assets and do not route `/api/*` to the
  SPA fallback. API requests must reach FastAPI.
- Configure host-level CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`,
  and frame protection, then verify actual deployed responses. The API's
  middleware does not configure static-host headers.
- Do not commit `.env.production` or real build secrets. Vite variables are
  browser-visible.

```text
SPA fallback: REQUIRED
/api/* excluded from SPA fallback: REQUIRED
Production static host: TBD
```

## 5. Backend deployment plan

- Runtime: Python `>=3.13`, dependencies from `backend/pyproject.toml` and
  `backend/uv.lock`.
- Start from `backend/` so `.env` discovery behavior is predictable, or inject
  all settings through the host environment.
- Packaged command: `uv run start` (console entry point `app.main:start`).
- Bind port: current packaged start uses `8000`; a platform requiring a
  dynamic port needs an intentional code/config change before selection.
- Workers: exactly one process/worker while abuse state is process-local.
- Production flags: `ENVIRONMENT=production`, `DEBUG=false`,
  `DEV_TEST_MODE=false`, exact `ALLOWED_HOSTS`, and production secret-store
  configuration.
- Liveness: `/health`. Readiness: `/ready`, which performs a bounded read-only
  Supabase query and returns a generic 503 when it fails.
- Shutdown: allow the ASGI server/platform to stop accepting requests and drain
  in-flight work. Public conversations persist in browser localStorage; no
  anonymous transcript is held on the server. Concurrency leases release in
  `finally` for handled requests.
- Proxy headers remain disabled until the real proxy hop/address and trust
  boundary are known.

## 6. Supabase environment strategy

The linked project is not classified in repository evidence. Before any
migration operation, an operator must identify whether it is development,
staging, or production and confirm the project reference against the intended
environment through the approved secret/connection mechanism.

```text
Development: local Supabase CLI project/config exists; Docker currently unavailable
Staging: NOT CONFIGURED
Production: NOT IDENTIFIED / NOT CONFIGURED
```

Do not treat local Supabase as staging or use the currently linked target for a
production migration until its ownership and environment are explicitly
confirmed. Prefer a disposable local database for SQL validation, followed by
a real staging project before production.

## 7. Database backup and recovery plan

### Current verified state

The Phase 7.9.1 read-only Supabase backup check reported:

```text
PITR: DISABLED
WAL-G support indicator: enabled
Available physical backups: 0
Backup availability: NO
Recovery capability: NOT VERIFIED
Restore procedure: NOT DOCUMENTED / NOT TESTED
```

The CLI exposes `supabase db dump` for remote schema/data exports. No dump was
created in this phase. A dump command's existence does not prove a complete,
consistent, confidential, retained, or successfully restorable backup. Any
logical-export proposal must specify included schemas/data/roles, encryption,
secure storage, retention, and a restore test in an isolated project.

### Required recovery path

Before migrations, the project owner must select and establish one supported
recovery mechanism: enable an appropriate Supabase PITR/backup plan after
confirming plan support and cost, or produce a supported logical/physical backup
with a documented isolated restore procedure. No plan or billing change is
authorized by this phase.

An available backup is insufficient on its own. Require a successful restore
exercise into an isolated compatible Supabase project and verify application
schema, required data, extensions/functions, grants, and ability to connect.
Protect exported data as sensitive production data; never place it in the repo.

```text
PITR: DISABLED (last observed)
Backup: NO physical backups available (last observed)
Recovery: NOT VERIFIED
Restore procedure: NOT DOCUMENTED / NOT TESTED
```

## 8. Pending migration chain and dependencies

The linked CLI's non-applying dry run with `--include-all` reported exactly:

```text
20260914000000_phase_6_11_student_notifications.sql
        ↓
20260928000000_phase_7_2_public_knowledge_policy.sql
        ↓
20260928010000_phase_7_4_public_rag_hardening.sql
```

Earlier required institution/student, knowledge/document/version, processing,
pgvector, embedding, and tenancy tables/RPC migrations are present in the
remote ledger. The pending Phase 6.11 migration is a predecessor by timestamp
and must be applied first by the normal migration system even though it is not
a dependency of the public knowledge RPC.

### Phase 6.11 migration review

- Creates `public.student_notifications` with student and institution foreign
  keys, controlled type check, read-state fields, and timestamps.
- Adds student/created, institution, partial unread, and partial unique source
  indexes.
- Creates/replaces `trg_student_notifications_tenant_guard()` and adds a
  before-insert/update trigger that derives tenant from the student row.
- Grants SELECT/INSERT/UPDATE/DELETE to `service_role` only in this migration.
- No data backfill or delete/drop appears in the SQL.
- The table is `IF NOT EXISTS` and indexes are `IF NOT EXISTS`, but the trigger
  creation has no preceding `DROP TRIGGER IF EXISTS`; the file is not safe as
  an arbitrary rerun. Apply it exactly once through migration history.
- Rollback requires careful removal of trigger/function/table and would delete
  notification data created after application; no down migration exists.

### Phase 7.2 migration review

- Adds `knowledge_sources.visibility` with non-null restricted default.
- Recreates the visibility check constraint and adds the policy index.
- Updates published FAQ/notice/handbook rows to public; this is a data
  transformation and materially changes anonymous eligibility.
- Creates `search_public_knowledge_chunks` with tenant, public visibility,
  publication, effective dates, version lifecycle, processing, embedding, and
  provenance joins.
- Revokes RPC access from `PUBLIC`, `anon`, and `authenticated`; grants only
  `service_role`.
- No table drop or row delete. There is no rollback migration; restoring the
  old state requires the verified recovery path or a separately reviewed
  forward fix. The update could re-publicize intentionally restricted eligible
  rows if this migration is manually rerun, so never use it as a repair script.

### Phase 7.4 migration review

- Replaces the same RPC definition, preserving all Phase 7.2 filters/grants.
- Requires match count from 1 through 20, limits results to 20, requires a
  completed processing run, and checks 1536 embedding dimensions.
- No data update/delete, table drop, or schema column change.
- No down migration; restore or a reviewed forward migration is required to
  reverse it safely.

## 9. Migration dry run and gate

The Supabase CLI supported two relevant operations:

- `supabase db push --dry-run --linked --include-all` succeeded and printed the
  three migrations above. It explicitly did not push/apply migrations.
- `supabase db reset --local` is the disposable local migration execution
  mechanism, but could not be run because Docker is installed without a running
  Docker daemon. Therefore SQL parsing/execution, function creation, indexes,
  and constraint behavior have not been validated by a local database dry run.

Do not substitute a linked/remote dry run for an isolated execution test. Once
a disposable local database or staging project is available, execute the full
chain in order and verify the schema/RPC contracts before opening the remote
migration gate.

### MIGRATION GATE

- [ ] Production/staging target and environment owner confirmed
- [ ] Correct Supabase project confirmed for that target
- [ ] PITR or backup available
- [ ] Restore procedure documented and restore test passed
- [x] Migration chain reviewed
- [ ] Disposable local/staging dry run passes
- [ ] Required production environment variables verified
- [x] Failure stop/recovery plan documented
- [ ] Change window and operator approved by project owner

```text
DO NOT APPLY REMOTE MIGRATIONS while any unchecked gate item remains.
Migration ledger history must only be written by the migration system;
never edit it manually or use it as a checklist.
```

## 10. Migration failure procedure

```text
Migration fails
  -> stop the migration command and deployment; do not continue later files
  -> preserve the exact CLI output and migration version in restricted logs
  -> do not edit the migration ledger or rerun a partially applied file blindly
  -> compare actual schema/data with the last verified backup and migration state
  -> use the approved restore/PITR process if recovery is required
  -> restore into isolation first when practicable and verify schema/data
  -> investigate and prepare a reviewed corrective migration
  -> rerun the complete intended chain in disposable/staging environment
  -> schedule a new approved production migration window
```

Application rollback does not reverse database changes. Do not deploy an older
application artifact if it is incompatible with the current schema.

## 11. Production secrets and environments

Production secrets must live in the selected host's managed secret store or
protected runtime environment variables, never tracked files or frontend Vite
variables. Required server secrets include Supabase service key, R2 access key
and secret, and OpenRouter API key. Required non-secret server configuration
includes Supabase URL/publishable key/JWKS URL, R2 endpoint/bucket,
`ENVIRONMENT`, `DEBUG=false`, `DEV_TEST_MODE=false`, `ALLOWED_HOSTS`, and
`AI_PROVIDER=openrouter`. `VITE_API_BASE_URL=/api` is public configuration.

Use independent development, staging, and production credentials/projects.
Staging is not configured. Do not repurpose local `.env` values as production
secrets and never commit `.env.production` with real values.

## 12. TLS, DNS, routing, and proxy plan

- TLS terminator: **TBD, selected platform required**.
- DNS names: **TBD, domain owner required**. Use placeholders such as
  `<site-domain>` and `<api-domain>` in planning; do not invent real names.
- Required behavior: HTTP redirects to HTTPS before application content or API
  responses are served publicly.
- Same-origin target shape: `https://<site-domain>/` for frontend,
  `/public-chat/<code>` for SPA, and `/api/*` routed to FastAPI. Keep `/api/*`
  out of SPA fallback.
- Backend `ALLOWED_HOSTS` must list exact chosen backend hostnames; no wildcard
  or development hosts in deployed settings.
- CORS remains absent for a same-origin deployment. A separate-origin design
  needs explicit frontend origin allow-listing and separate TLS verification.
- Proxy identity: no trusted proxy configured. Continue ignoring forwarding
  headers until the selected platform's trusted proxy addresses and hop count
  are known and tested.
- Frontend static-host response headers must be inspected on the live origin;
  backend API middleware does not prove frontend policy.

## 13. Monitoring and alerting plan

No monitoring platform, metrics exporter, dashboard, or alert configuration
exists in the repository. Minimum production signals to collect through the
selected hosting/monitoring service are:

- uptime and readiness failures;
- HTTP 4xx/5xx counts and rate;
- request latency;
- 429 and 503 counts;
- provider timeout/auth/network failures;
- Supabase/database failures;
- process CPU/memory and restart events.

Minimum alerts: service unavailable, sustained/high 5xx rate, repeated provider
failure, database unavailable, 429/503 spike, and resource exhaustion/restart
loop. Preserve current content-free logging: never collect questions, generated
answers, auth tokens, provider keys, raw SQL, or private document text.

```text
MONITORING: EXTERNAL DEPLOYMENT PREREQUISITE
ALERTING: EXTERNAL DEPLOYMENT PREREQUISITE
```

No analytics platform is proposed.

## 14. Application and database rollback

### Application

The eventual host must retain immutable deployment artifacts and document its
supported rollback action from deployment N to N-1. No host exists, so a
platform command or tested rollback cannot be specified yet.

### Database

Database recovery is an independent procedure based on verified Supabase
backup/PITR or a tested supported export/restore. Pending migrations have no
down migrations, and Phase 7.2 changes public eligibility data. Application
rollback does not roll back schema/data. Verify recovery in an isolated project
and preserve the migration history through the CLI migration mechanism.

## 15. Abuse controls and scaling

Current request rate limits and concurrency counters are process-local. Keep
one backend process and one worker for initial deployment. Horizontal scaling
is blocked until the selected edge or shared service provides distributed,
atomic rate limiting and concurrency enforcement and a trusted client-IP
derivation is documented. No Redis or other service is selected or introduced
by this plan.

## 16. Cost considerations

Potential recurring cost categories are frontend/backend hosting, Supabase
database and backup/PITR plan, R2 requests/storage/egress, OpenRouter embedding
and generation usage, domain/DNS, and monitoring/alerting. No exact prices or
plans are claimed because neither provider plans nor traffic budgets are
selected. Confirm plan limits, retention, and spend controls with the project
owner before enabling paid services.

## 17. DEPLOYMENT GATE

- [ ] Frontend/backend hosting selected
- [ ] Production hostname and DNS owner selected
- [ ] TLS termination and HTTP-to-HTTPS redirect confirmed
- [ ] SPA fallback configured for `/public-chat/*`
- [ ] `/api/*` routed to FastAPI, not SPA
- [ ] Exact production `ALLOWED_HOSTS` configured
- [ ] Same-origin topology confirmed or explicit CORS configured
- [ ] Production secrets installed in managed secret store
- [ ] `/health` and `/ready` probes configured
- [ ] Monitoring and required alerts available
- [ ] Application and database recovery procedures verified
- [x] Single-worker deployment enforced by packaged start
- [ ] Real deployed security headers and browser smoke tests passed

Do not deploy publicly while required topology and gate items remain open.

## 18. Current gate results and next actions

```text
PITR: DISABLED
Backup availability: NO (zero physical backups in last provider check)
Recovery capability: NOT VERIFIED
Migration dry-run listing: PASS (non-applying linked CLI dry run)
Disposable migration execution: NOT RUN (Docker daemon unavailable)
Remote migrations: DO NOT APPLY
```

Next actions, in order:

1. Project owner identifies the linked Supabase environment and authorizes the
   intended staging/production target.
2. Project owner selects a supported recovery product or backup/export
   approach, confirms any billing/retention requirements, then completes an
   isolated restore test.
3. Start Docker or provide a disposable staging project; run the full ordered
   migration chain and verify table, trigger, policies/grants, index, RPC
   signature/return fields, and local public eligibility matrix.
4. Reconfirm migration ledger and backup state, then apply only through the
   approved ordered Supabase migration mechanism after all migration-gate
   checks pass.
5. Select hosting, DNS, TLS, secrets, routing, monitoring, alerts, and rollback
   with the project owner; fill in exact host values and deploy the SPA/API
   routing rules.
6. Verify live headers/routes, database readiness, public retrieval/generation,
   browser refresh, safe errors, logs, alerts, and rollback path.

## 19. Verification record

```text
Backend:
  DEBUG=true uv run pytest -q tests
  2128 passed, 15 skipped, 6 warnings

Frontend:
  npm.cmd run test -- --pool=vmThreads --maxWorkers=1
  50 files passed, 431 tests passed

TypeScript:
  npx.cmd tsc --noEmit -p tsconfig.json
  exit 0

Production build:
  npm.cmd run build
  97 modules transformed; passed

Supabase pending-migration dry-run listing:
  supabase db push --dry-run --linked --include-all
  exit 0; listed exactly the three pending migrations; no migrations applied

Disposable local SQL run:
  supabase db reset --local
  NOT RUN — Docker daemon unavailable

Diff hygiene:
  git diff --check
  exit 0; existing line-ending notices only
```

## 20. Readiness and phase status

```text
Demo readiness: NOT READY
Single-instance production: NOT READY
Horizontal scaling: NOT READY
```

```text
PHASE 7.9.2 STATUS: INCOMPLETE
```

The plan and gates are documented, but recovery capability, disposable SQL
execution, production platform/hostname/TLS/routing/monitoring, and deployment
verification remain unresolved prerequisites.
