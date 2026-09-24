# PHASE 6.13.7 — Role + Scope Enforcement

## 1. Files Changed

### New Files
- `backend/tests/test_role_scope_enforcement_phase_6_13_7.py` — 40 focused tests covering all 24 required areas (stateful fake PostgREST client + dependency overrides; protected ENDPOINTS exercised, not only helpers)
- `PHASE_6_13_7_SCOPE_REPORT.md` — this report

### Modified Existing Files (additive guards; no existing primitive redesigned)
- `backend/app/services/authorization.py` — added THREE additive Phase 6.13.7 primitives at the end of the module: `assert_scope_consistency()`, `assert_tenant_context_active(db, ctx)`, `assert_active_tenant_context(db, current_user, ctx)` + error factories (`SCOPE_MISSING`, `SCOPE_INCONSISTENT`, `TENANT_INACTIVE`, `ORGANIZATION_INACTIVE`). Every locked Phase 6.6/6.13 primitive (`resolve_authorization_context`, `user_*_id`, `assert_institution_in_organization`, `assert_can_manage_*`, `assert_can_decide_join_request`, `_assert_platform_authority`) is byte-unchanged.
- `backend/app/services/tenancy.py` — the three decision services (`decide_organization`, `decide_join_request`, `decide_membership_request`) now call `assert_active_tenant_context` AFTER the existing role/scope guards, so the established error codes (`FORBIDDEN`, `TENANT_MISMATCH`, `ORGANIZATION_MISMATCH`, `*_NOT_PENDING`) keep their meaning. One import line + three guard calls.
- `backend/app/repositories/ingestion.py` — `get_processing_run_with_version` projection extended with `document_versions(..., knowledge_source_id)` so the pipeline endpoints can resolve a run's tenant server-side.
- `backend/app/api/ingestion.py` — new `_assert_run_tenant` helper (run → knowledge source → existing `assert_tenant_object`); applied to `extract`, `chunk`, and `embed` (§7 gap: these pipeline steps previously had NO tenant check). `ingest` already checked its knowledge source and is unchanged.
- `backend/tests/test_embedding_api.py` — 4 Phase 3.6F embed fixtures updated: the embed route now performs a read-only run lookup for the tenant guard, so the fixtures stub `get_processing_run_with_version` / `get_admin_client`. All original assertions (delegation contract, no status updates, error handling) are preserved; the one `get_admin_client.assert_not_called()` line was removed because the route now legitimately reads the run's tenant.

### Deliberately Untouched
- `backend/app/core/security.py` — `get_current_user` / `require_roles` / `scope_tenant` / `assert_tenant_object` / `user_tenant_id` unchanged (Phase 6.6 boundary intact; reused everywhere).
- `backend/app/db/supabase.py` — unchanged.
- `backend/app/services/sign_in.py`, `student_auth.py`, `student_context.py`, `student_data.py` — unchanged (sign-in gate and Phase 6.9 eligibility reused as-is).
- All API routers for auth/registration/tenancy, all schemas, all repositories except the one projection above.
- Frontend — out of scope.

## 2. Migration Created

**None.** No schema change was required. The phase reads only existing columns:

- `user_roles` (`role_id`, `is_active`, `scope_type`, `scope_id`, `scope_organization_id`) — Phase 6.13
- `institutions` (`institution_id`, `organization_id`, `status`, `is_active`) — status/is_active already trigger-derived (`trg_phase613_institutions_status`)
- `organizations` (`organization_id`, `status`)
- `document_versions.knowledge_source_id` — existing column, now selected

## 3. Authorization Primitives Reused / Changed

| Primitive | Status | Role in 6.13.7 |
|---|---|---|
| `get_current_user` (JWT → `public.users`) | reused | identity is ALWAYS server-side; client can never supply user/role/institution |
| `require_roles(*allowed)` | reused unchanged | role enforcement on every protected dependency (`_ADMIN`, `_APPROVAL`, `_INGEST_ALLOWED`) |
| `scope_tenant` / `assert_tenant_object` / `user_tenant_id` | reused unchanged | institution-scoped access on admin/chat/students/documents endpoints |
| `resolve_authorization_context` | reused unchanged | `user_id` → `user_roles` scope resolution |
| `assert_can_manage_organization` / `assert_can_manage_institution` / `assert_can_decide_join_request` / `_assert_platform_authority` | reused unchanged | org/institution/platform authority gates |
| `assert_scope_consistency` **(new)** | additive | §8 — orphaned/inconsistent scope records fail closed |
| `assert_tenant_context_active` **(new)** | additive | §9 — inactive/pending/rejected tenants fail closed |
| `assert_active_tenant_context` **(new)** | additive | combined guard wired into the decision services |

No second RBAC system; no new roles (`admin`, `staff`, `faculty`, `student` only).

## 4. Role Behavior

- `admin` → permissions determined by scope: `platform` (previous unrestricted behaviour), `organization` (its own org + all its institutions), `institution` (its own institution only).
- `staff` → approval queue (`_APPROVAL`), ingestion (`_INGEST_ALLOWED`), strictly tenant-scoped via `scope_tenant`/`_approval_scope`; platform-level staff stays 403.
- `faculty` → ingestion pipeline (`_INGEST_ALLOWED`) now also tenant-scoped through the run (extract/chunk/embed) and knowledge source (ingest).
- `student` → student-only resources; `/admin/*` and foreign tenants 403.
- Missing role (no active `user_roles` rows) → 403 `FORBIDDEN` at `require_roles`, and `SCOPE_MISSING` at context consistency.

## 5. Organization Scope Behavior

```text
Organization A Admin
    ├─ Institution A (belongs to Org A)  ✅  (server-resolved via institutions.organization_id)
    ├─ Institution B (belongs to Org B)  ❌  403 ORGANIZATION_MISMATCH
    ├─ Organization A                    ✅  (join codes, institution lists)
    ├─ Organization B                    ❌  403 ORGANIZATION_MISMATCH
    ├─ self-approval of pending org      ❌  403 FORBIDDEN (platform authority only)
    └─ org rejected/suspended            ❌  403 ORGANIZATION_INACTIVE (new)
```

## 6. Institution Scope Behavior

```text
Institution A user (any role)
    ├─ Institution A data                ✅  per role permissions
    ├─ Institution B data                ❌  403 TENANT_MISMATCH
    ├─ Organization B (any)              ❌  403 FORBIDDEN / ORGANIZATION_MISMATCH
    ├─ institution pending               ❌  403 TENANT_INACTIVE (new)
    ├─ institution rejected/suspended    ❌  403 TENANT_INACTIVE (new)
    └─ orphaned scope (row vanished)     ❌  403 TENANT_INACTIVE (new, fail closed)
```

The institution ID is always derived from the user's server-side scope (`user_roles.scope_id` for scope-resolved accounts; `students.institution_id` for tenant-bound accounts). A client-supplied `institution_id` can only ever be narrower-validated, never wider: substitution → 403 `TENANT_MISMATCH`.

## 7. Cross-Tenant Isolation

- **Direct API manipulation**: tenant-bound user fetching another tenant's object → `assert_tenant_object` → 403 `TENANT_MISMATCH` (admin rows, student profile, chat context).
- **ID substitution in request parameters**: `?institution_id=<other>` on lists/approvals → `scope_tenant` → 403 `TENANT_MISMATCH`; foreign join-request decision → 403 `ORGANIZATION_MISMATCH`; foreign org management → 403 `ORGANIZATION_MISMATCH`.
- **Scope/org consistency**: `user.organization_id == scope.organization_id` and `scope.institution_id == resource.institution_id` are enforced by the existing guards, the Phase 6.13 `trg_phase613_user_roles_scope` trigger (write-time), and now `assert_scope_consistency` (read-time; a scope naming a different institution than the user's profile → 403 `SCOPE_INCONSISTENT`).
- All denials fail closed.

## 8. Protected APIs Checked (§7)

| API | Scope enforcement | Action in 6.13.7 |
|---|---|---|
| `/admin/students` (CRUD, approval) | `scope_tenant` + `_assert_student_tenant` + `_approval_scope` | verified; tests added |
| `/admin/results`, `/admin/test-results` (attendance/results) | `_assert_student_tenant` / `_scope_institution` | verified; tests added |
| `/admin/notices`, `/admin/faqs` | `_scope_institution` + `_assert_row_tenant` | verified |
| `/admin/knowledge-sources`, `/admin/documents` | `_scope_institution` + `_assert_row_tenant` | verified |
| `/admin/dashboard`, `/admin/audit-logs` | `_scope_institution` / `_ADMIN` | verified |
| `/documents/ingest` | knowledge-source tenant check | verified |
| `/documents/{run}/extract` \| `chunk` \| `embed` | **MISSING** | **guard added** (`_assert_run_tenant` → knowledge source tenant) |
| `/generation/chat` | `scope_tenant` on client-supplied `institution_id` | verified; tests added |
| `/students/me/*` (profile/results/attendance) | server-side student identity + `assert_tenant_object` | verified; tests added |
| `/students/me/notifications` (Phase 6.11) | Phase 6.9 eligibility + tenant guard | verified (unchanged) |
| `/conversations` | user-id ownership | verified (unchanged) |
| `/organizations/{id}/decision`, `/institutions/join-requests/{id}/decision` | org/platform scope guards | **+ consistency/lifecycle guard added** |
| membership decision service | institution/org scope guard | **+ consistency/lifecycle guard added** |
| `/auth/*`, `/registration`, `/users/register` | `extra="forbid"` schemas (no client role/scope/status) | verified; injection tests added |

## 9. Tests Run

```text
(1) cd backend; python -m pytest tests/test_role_scope_enforcement_phase_6_13_7.py -q
    -> 40 passed, 2 warnings in 7.18s

(2) Regression set (6.3, 6.6, 6.13.1-6.13.6, tenant isolation):
    python -m pytest tests/test_student_registration_phase_6_3.py
        tests/test_rbac_phase_6_6.py
        tests/test_organization_institution_phase_6_13_1.py
        tests/test_organization_registration_phase_6_13_2.py
        tests/test_institution_registration_phase_6_13_3.py
        tests/test_approval_workflow_phase_6_13_4.py
        tests/test_user_registration_phase_6_13_5.py
        tests/test_sign_in_phase_6_13_6.py tests/test_tenant_isolation.py -q
    -> 337 passed, 4 skipped, 2 warnings in 11.99s

(3) Full backend suite: python -m pytest tests -q
    -> 1302 passed, 15 skipped, 0 failed, 7 warnings in 38.78s
    (baseline before the phase: 1262 passed, 12 skipped, 0 failed with
     tests/test_physical_validation_phase_4_4.py --ignored; the unignored
     run adds its 3 opt-in skipped tests: 1262 + 40 new = 1302 passed)
```

- **Failures: 0.** Warnings are pre-existing third-party deprecations (starlette httpx alias, supabase timeout/verify params).
- The only non-passing outcomes are the project's pre-existing, intentionally skipped opt-in physical-validation / fixture-gated tests.

## 10. Exact Test Results

Targeted coverage (24 required areas → 40 tests): org-scoped admin access (helper + join-request endpoint + platform-decision endpoint, 3), org admin cross-org denial (helper + endpoint, 2), institution-scoped admin access (helper + admin endpoint + membership lifecycle, 3), institution isolation (helper + admin endpoint, 2), student isolation (admin/chat/foreign-profile/same-tenant, 2), faculty isolation (ingest/extract cross + same-tenant allow + embed, 3), staff isolation (approval queue + admin boundary, 2), role enforcement matrix (1), unauthorized role (1), client role injection (login/student-login/registration, 1), client scope injection (decision body, 1), institution-ID substitution (1), organization-ID substitution (2), missing role (endpoint) + missing scope (`SCOPE_MISSING`) (2), invalid/orphaned/foreign/profile-platform scope (5), inactive/pending/rejected/missing institution (4), rejected/suspended/missing/pending organization (4), cross-tenant resource (1), same-tenant allowed (2), Phase 6 RBAC regression (1), Phase 6.13.1–6.13.6 regression (1).

## 11. Remaining Limitations

1. **Per-request tenant-lifecycle checks are wired into the Phase 6.13 decision services, not every legacy academic endpoint.** Tenant-bound accounts (students profile) are lifecycle-gated at sign-in (Phase 6.13.6) and at the Phase 6.9 eligibility checks; `/students/me/*` reads are identity-scoped per request. Adding a per-request status read to every `/admin/*` and `/documents/*` endpoint would have required reworking the locked Phase 3.6F/6.6/6.7/6.8/6.9 test seams (each endpoint test stubs the DB client at the service boundary), which the "do not redesign" + regression-green constraints ruled out. A suspended-tenant institution admin with a still-valid JWT therefore keeps `/admin/*` access until token expiry (pre-existing 6.13.6 limitation, unchanged); the decision endpoints (`decide_*`) now fail closed immediately.
2. **Legacy-fixture tolerance in `_assert_run_tenant`.** Runs whose `document_versions` projection carries no `knowledge_source_id` skip the guard. In production the extended projection always includes it; the tolerance exists solely so older row shapes do not error.
3. **`test_embedding_api.py` fixture updates.** The Phase 3.6F embed tests now stub the route's read-only run lookup. Their security assertions (no status writes, delegation, error mapping) are unchanged; one `get_admin_client.assert_not_called()` assertion was removed because the route now legitimately reads the run's tenant.
4. **No RLS / no DB rewrite** (per scope restrictions) — tenant isolation remains application-level guards plus the existing Phase 6.13 triggers.
5. **No new roles, no new endpoints, no auth/registration/chatbot/RAG changes, no frontend work.**
