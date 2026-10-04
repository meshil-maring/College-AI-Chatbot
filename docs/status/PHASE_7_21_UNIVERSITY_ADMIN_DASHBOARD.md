# Phase 7.21 — University Admin Dashboard

## Status

**COMPLETE**

The University Admin operational dashboard is now a real, tenant-safe
operational overview of exactly one institution. The existing `AdminDashboard`
was audited and rebuilt in place (no second dashboard), the existing
`GET /api/v1/admin/dashboard` endpoint was extended with an explicit typed
contract, and every metric is derived from the server-resolved Phase 7.20
authorization context.

No schema change, no migration, no remote change, and no email delivery
occurred.

## Dashboard Architecture

```
Browser (AdminShell, view = 'dashboard', the default landing view)
  -> AdminDashboard.tsx  (one GET per load; loading / zero / error / retry)
  -> adminApi.getDashboardSummary(accessToken)     <-- sends NO institution_id
  -> GET /api/v1/admin/dashboard
       -> require_institution_roles("admin")      [Phase 7.20, unchanged]
            -> resolve_institution_authorization_context()
               server-owned user_roles.scope_id + institutions lifecycle
  -> admin_dashboard.get_dashboard_summary(institution_id=resolved)
       -> _institution_summary   tenancy.get_institution_by_id
       -> _students_summary      _count(students, ...)
       -> _knowledge_summary     _count / _count_in / _count_related
       -> _communication_summary _count(faqs|notices) + knowledge_repo.list_notices
       -> _academics_summary     _count_related(!inner students)
  -> DashboardResponse  (app/schemas/admin_dashboard.py, explicit response_model)
```

The frontend renders the response; it never derives a metric of its own.

## Dashboard Contract

`DashboardResponse` — the complete, closed payload:

| Section | Field | Meaning / source |
|---|---|---|
| `institution` | `name`, `code`, `status` | the caller's own `institutions` row (safe display fields only) |
| `students` | `total` | all `students` rows for the institution |
| | `pending_approvals` | `approval_status = 'pending'` — same predicate as the approval queue |
| | `approved` | `approval_status = 'approved'` |
| | `active` | academic lifecycle: `status = 'active'` AND `is_active` |
| `knowledge` | `sources_total` | all `knowledge_sources` for the institution |
| | `sources_active` | lifecycle in the existing `ACTIVE_LIFECYCLE_STATUSES` (draft / under_review / approved / published) |
| | `documents_total` | `documents` joined to the institution's `knowledge_sources` |
| | `failed_processing_runs` | **`null` = Unavailable** (see Limitations) |
| `communication` | `active_faqs` | `faqs` where `is_active` |
| | `active_notices` | `notices` where `is_active` |
| | `recent_notices[]` | bounded (5), `{title, category, priority, published_at}` — no ids, no body |
| `academics` | `attendance_records` | `student_attendance` via `!inner students` |
| | `test_results` | `test_results` via `!inner students` |
| | `results` | `student_results` via `!inner students` |
| `quick_actions` | `[{view, label, description}]` | navigation to existing AdminShell views |

There is no `tests` table in this schema, so "tests" is represented by
`test_results` rather than by an invented parallel metric. No metric is
fabricated: an unresolvable metric is `null`, and `0` always means "measured,
none".

The previous `{counts, recent_audit}` shape is **removed**. `recent_audit`
returned raw `admin_audit_log` rows (`actor_user_id`, `record_data`,
`ip_address`, `user_agent`), which are internals the dashboard must not surface.

## Authorization

Phase 7.20 is reused unchanged. The endpoint keeps the single shared dependency:

```python
_ADMIN = require_institution_roles("admin")
```

The institution passed to the service is `user_tenant_id(current_user)` — the
value that dependency resolved from the server-owned `user_roles` institution
grant and verified against the institution lifecycle. The dashboard service
never re-derives a tenant and never accepts one from the request.

**The `institution_id` query parameter was removed from the endpoint.** It is no
longer accepted, so a client-supplied tenant can neither widen nor redirect the
scope; FastAPI ignores it and the caller receives its own institution's data.
The frontend client no longer offers the parameter either. A test asserts the
route declares zero query parameters.

## Tenant Isolation

Verified with `tests/test_phase_7_21_university_admin_dashboard.py` using two
institutions (A/B), two admins (A/B), and the real Phase 7.20 guard (only the
authorization module's data client is stubbed):

| Check | Result |
|---|---|
| Admin A receives A metrics | pass |
| Admin B receives B metrics | pass |
| Admin A never sees B data (name, code, id, counts) | pass |
| Admin B never sees A data | pass |
| Service receives only the resolved tenant | pass |
| `institution_id` / `role` / `scope_type` / `institution_code` / `code` / `tenant` manipulation does not alter the response (6 parametrized cases, byte-identical JSON) | pass |
| Foreign `institution_id` is never echoed back | pass |
| Tenantless admin denied | pass |
| Platform-scoped `admin` role row denied (no privilege inheritance) | pass |
| Inactive institution denied (`TENANT_INACTIVE`) | pass |
| Inactive account denied (`ACCOUNT_INACTIVE`) | pass |
| Zero-data institution returns a normal 200 | pass |
| student / staff / faculty denied | pass |
| Super Admin denied on the dashboard; `/platform/*` unchanged | pass |
| Unauthenticated request rejected (401) | pass |
| Internal error normalized (no SQL, host, or table text) | pass |
| Response contains no forbidden key (recursive walk) | pass |
| Exactly one dashboard endpoint, explicit response model, no query params | pass |

## Existing Features Reused

- **Endpoint** `GET /api/v1/admin/dashboard` (extended, not duplicated).
- **Authorization** `require_institution_roles`, `resolve_institution_authorization_context`, `user_tenant_id`.
- **Service** `app/services/admin_dashboard.py` — kept `_count` / `_count_related` (the Phase 7.20 tenant-safe primitives) and added `_count_in`.
- **Repositories** `admin_knowledge.ACTIVE_LIFECYCLE_STATUSES`, `admin_knowledge.list_notices`, `tenancy.get_institution_by_id` (the same read the Phase 7.20 guard uses).
- **Frontend** `AdminDashboard`, `AdminShell`, `adminNavigation`, `adminApi.requestJson` (session-expiry handling inherited), Tailwind design language, AuthProvider state.
- **Screens behind the quick actions** approvals, students, documents, faqs, notices, attendance, results, test-results — all already implemented and authorized.

## New Changes

**Created**
- `backend/app/schemas/admin_dashboard.py` — the explicit typed contract.
- `backend/tests/test_phase_7_21_university_admin_dashboard.py` — 32 focused tests.
- `backend/tests/dashboard_contract.py` — shared valid-response builder for tests.
- `frontend/src/test/adminDashboardFixtures.ts` — shared typed dashboard fixtures.
- `frontend/src/features/admin/AdminDashboard.test.tsx` (rewritten, 11 tests).
- `docs/status/PHASE_7_21_UNIVERSITY_ADMIN_DASHBOARD.md` (this file).

**Modified**
- `backend/app/services/admin_dashboard.py` — builds the typed response; audit feed removed; quick actions declared.
- `backend/app/api/admin.py` — dashboard endpoint: typed `response_model`, `institution_id` query parameter removed.
- `backend/tests/test_admin_dashboard_service.py`, `test_admin_api.py`, `test_admin_experience_phase_6_19.py`, `test_cross_role_integration_phase_6_20.py` — updated to the new contract (guarantees preserved, not weakened).
- `frontend/src/types/admin.ts` — new dashboard types replacing `{counts, recent_audit}`.
- `frontend/src/services/adminApi.ts` — `getDashboardSummary(accessToken)` sends no tenant.
- `frontend/src/features/admin/AdminDashboard.tsx` — rebuilt in place.
- `frontend/src/features/admin/AdminShell.tsx` — passes `onNavigate` for quick actions.
- `frontend/src/App.test.tsx`, `CrossRoleIntegration.test.tsx`, `CrossRoleSessionLifecycle.test.tsx`, `AdminShell.test.tsx`, `adminApi.test.ts` — fixtures/assertions updated to the new contract.

No new dependency, no new framework, no new module, no new endpoint.

## Empty States

A newly created institution (0 students, 0 documents, 0 FAQs, 0 notices, 0 tests,
0 results, 0 attendance records) is a **normal 200**, not an error:

- Backend: every count is `0`, `recent_notices` is `[]`, and the endpoint
  succeeds (`test_zero_data_institution_renders_successfully`).
- Frontend: an explicit banner — "This institution has no students, knowledge or
  notices yet. Start with a quick action below." — plus zeroed metric tiles and
  "No active notices." No `role="alert"` is rendered.

A metric that is unresolvable is distinct from zero: it renders as "Unavailable",
never as `0`.

## Error Handling

**Backend** — existing conventions, no new error shape. `AppError` renders the
standard `{"error": {"code", "message"}}` envelope; an unexpected exception is
caught by the existing global handler and returned as a generic
`INTERNAL_ERROR` 500. SQL text, host names, table names, and stack traces are
never returned. Authorization failures reuse the Phase 7.20 codes
(`ACCOUNT_INACTIVE`, `SCOPE_MISSING`, `SCOPE_INCONSISTENT`, `TENANT_INACTIVE`).

**Frontend** — four explicit states: loading (`role="status"`), success,
zero-data, error (`role="alert"` + a manual **Retry**). Retries are strictly
user-initiated; there is no automatic or aggressive retry, and exactly one
request is issued per load. Session expiry is inherited from the shared API
client via `notifySessionExpired`.
## Tests

| Check | Command | Result |
|---|---|---|
| Focused Phase 7.21 | `pytest tests/test_phase_7_21_university_admin_dashboard.py` | **32 passed** |
| Dashboard service + API | `pytest tests/test_admin_dashboard_service.py tests/test_admin_api.py` | **41 passed** |
| Combined focused | the three files above | **73 passed** |
| Admin regression | `test_admin_experience_phase_6_19.py`, `test_admin_api.py`, `test_admin_dashboard_service.py` | **passed** |
| RBAC / tenant isolation | `test_phase_7_20_*`, `test_role_scope_enforcement_phase_6_13_7`, `test_security_final_validation_phase_6_13_9`, `test_cross_role_integration_phase_6_20`, `test_admin_experience_phase_6_19` | **182 passed** |
| Super Admin regression | `test_phase_7_12_*`, `test_phase_7_13_*`, `test_phase_7_14_*`, `test_phase_7_20_*` | **178 passed** |
| Complete backend suite | `pytest tests` | **2492 passed, 27 skipped** (baseline 2451 + 41 new) |
| Backend, production-like (`DEBUG=false`) | `DEBUG=false pytest tests` | **2490 passed, 2 failed, 27 skipped** |
| Frontend | `npm test` | **58 files / 519 tests passed** (baseline 510 + 9 new) |
| TypeScript | `npx tsc -b --force` | **passed** (exit 0) |
| Production build | `npm run build` | **passed** — 112 modules transformed |
| Artifact / secret scan | `node scripts/verify_frontend_build_security.mjs` | **PASSED** (4 dist files scanned) |
| Frontend secret guard | `test_phase_7_14_...::test_no_frontend_module_can_read_a_service_role_key` | **passed** |

**Environment-specific failures disclosed (not hidden):** the two `DEBUG=false`
failures are `test_conversational_rag.py::test_dev_diagnostics_attach_to_generation_metadata`
and `::test_standalone_question_diagnostics_rewritten_query_is_none`. They assert
development diagnostics that are intentionally absent when `DEBUG=false`, are
unrelated to authorization or the dashboard, and are **identical to the failures
recorded in the Phase 7.20 baseline**. This was verified by stashing all Phase
7.21 changes and re-running the baseline (`2 failed, 2449 passed, 27 skipped`).
Rerun with `DEBUG=true`: **all pass**.

One `test_complete_product_demo_phase_6_22.py` failure appeared in one
`DEBUG=false` run and did not reproduce across four subsequent full runs
(including two clean `DEBUG=false` runs) or in isolation. It is an
ordering/isolation flake in an untouched test file, not a product failure.

## Performance

- A **fixed** number of queries proportional to the number of *metrics* (not the
  number of rows): 4 student counts, 3 knowledge counts, 2 communication counts,
  3 academic counts, 1 institution read, 1 bounded notice list.
- No N+1: every aggregate uses `select(..., count="exact")`; no table is ever
  listed row-by-row to be counted in Python. A test asserts the students table
  is only ever count-aggregated.
- Tenant filtering happens **in the query** (`.eq("institution_id", ...)` or an
  `!inner` join), never in application code.
- The only list is `recent_notices`, explicitly bounded to 5
  (`RECENT_NOTICES_LIMIT`).
- **No** Redis, cache, background job, materialized view, event stream, metrics
  platform, or external analytics service was introduced.

## Security

- The endpoint declares `response_model=DashboardResponse`, so the payload is
  re-projected through explicit models; extra keys a service invents are dropped
  (tested).
- The recursive key-walk test denies: `institution_id`, `organization_id`,
  `user_id`, `auth_user_id`, `actor_user_id`, `audit_id`, `notice_id`,
  `faq_id`, `student_id`, `record_id`, `record_data`, `ip_address`,
  `user_agent`, `scope_type`, `scope_id`, `roles`, `role_assignments`,
  `service_role`, `password`, `token`, `api_key`, `authorization_context`,
  `counts`, `recent_audit`.
- Raw `admin_audit_log` rows are no longer queried or returned at all.
- No platform audit data, provider credentials, service-role information, or
  cross-tenant records appear in the response.
- The frontend renders only the declared sections; a test asserts no internal
  identifier, token, or secret-looking value reaches the DOM.
- Authorization remains server-side and unchanged: hiding a card or a quick
  action grants nothing.

## Remote Safety

- Remote Supabase changed: **NO**
- Migrations pushed remotely: **NO**
- Production users / roles / institutions modified: **NO**
- Production email sent / Mailgun invoked: **NO**
- No live server was started and no validation target was contacted. Only the
  local test suite, mocked clients, and the local production build were used.
- `supabase/migrations` is byte-identical to `HEAD`.

## Migration

**NONE**

Every dashboard metric is derivable from existing tables and columns, so no
schema change was required and none was created.

## Limitations

1. **`failed_processing_runs` is unavailable (`null`).** `document_processing_runs`
   has no `institution_id` column; its tenant is only reachable through a
   three-level nested embed (runs → document_versions → documents →
   knowledge_sources) that this phase deliberately does not introduce. It is
   reported as Unavailable rather than as a fabricated `0`. Resolving it would
   need either that embed or an immutable `institution_id` written server-side at
   write time — a schema change, out of scope here.
2. **No "tests" count.** This schema has no `tests` table; only `test_results`
   exist. "Tests" is therefore represented by `test_results` and is not
   double-counted as a separate metric.
3. **Recent activity was removed, not relocated.** The dashboard no longer shows
   a recent-activity feed. `admin_audit_log` has no immutable `institution_id`,
   so an institution-wide feed cannot be made tenant-safe without a schema
   change. Audit records remain available on the dedicated `/admin/audit-logs`
   surface, which Phase 7.20 already scoped per-actor.
4. **Student counts are separate aggregates.** `total`, `pending_approvals`,
   `approved`, and `active` are four `count="exact"` queries rather than one
   `GROUP BY`. This is a deliberate trade: the query count is constant and each
   query is index-supported (`idx_students_institution_approval`), which keeps
   the tenant filter in the query. A grouped aggregate would need an RPC or a
   view, i.e. a schema change.
5. **No institution branding beyond name/code.** The Phase 7.13 branding columns
   (`logo_url`, colours, welcome message) are platform-managed configuration and
   the University Admin has no branding-management surface, so they are not
   projected.
6. **No schema-level tenant constraint.** Supabase RLS is not used for these
   tables (service-role client plus application-layer authorization, the
   existing project architecture). The boundary remains the application layer,
   unchanged from Phase 7.20.
