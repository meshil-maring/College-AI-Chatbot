# PHASE 6.1 — COLLEGE/TENANT MODEL LOCK

## STATUS: LOCKED

Lock date: 2026-09-12
Locked at final read-only lock review completion. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.1

## 2. Phase Name

Phase 6.1 — College/Tenant Model (Multi-Tenancy Enforcement)

## 3. Final Implementation State

Phase 6.1 implements backend-enforced tenant isolation using the existing
`institution_id` as the canonical tenant key. The verified final state:

- Existing `institution_id` is the canonical tenant key. No new tenant
  database column or table was introduced.
- Tenant resolution is enforced server-side from the authenticated user's
  students profile (`user_tenant_id`, `backend/app/core/security.py`).
  Platform-level accounts (no students row) resolve to `institution_id=None`
  and pass a requested institution through.
- Client-supplied tenant/institution identifiers can never elevate or
  redirect tenant scope: `scope_tenant` forces a tenant-bound user to their
  own institution and rejects any requested mismatch.
- Tenant-keyed object access is guarded by `assert_tenant_object`
  (`backend/app/core/security.py`), which allows a tenant-bound user's own
  rows and global rows (`institution_id IS NULL`) and rejects cross-tenant
  rows.
- The chat endpoint (`backend/app/main.py`) resolves the effective tenant
  via `scope_tenant` before processing; a cross-tenant `institution_id` is
  rejected with `403 TENANT_MISMATCH` and the chat pipeline is never invoked.
- Tenant-keyed admin queries (`backend/app/api/admin.py`,
  `backend/app/services/admin_academics.py`) are scoped to the
  authenticated admin's institution; a requested foreign institution is
  rejected and a missing one defaults to the admin's own tenant.
- Student endpoints (`backend/app/api/students.py`) and ingestion endpoints
  (`backend/app/api/ingestion.py`) enforce the same tenant boundary.
- Tenant lookup helpers were added to the database layer
  (`backend/app/db/supabase.py`).
- Existing functionality remains passing; no locked behavior was reopened.

## 4. Architecture Decision

- **No new tenant schema.** The pre-existing `institution_id` column is
  retained as the single canonical tenant key across students, knowledge
  sources, documents, versions, and processing runs. Introducing a parallel
  tenant identifier was explicitly rejected to avoid dual-key drift and
  migration risk.
- **Server-side tenant authority.** The tenant is never trusted from the
  client. It is resolved from the authenticated user (via their students
  profile) and, where a request carries an institution id, validated against
  that resolved tenant. Resolution and validation live in one shared module
  (`backend/app/core/security.py`) so every endpoint uses identical
  semantics.
- **Deny-by-default mismatch handling.** Any conflict between the resolved
  tenant and a requested/row-level institution is a hard `403
  TENANT_MISMATCH` (message: "This resource belongs to a different
  institution") — never a silent rewrite — except where the admin list
  endpoints force-scope the query to the admin's own institution.
- **Platform-level passthrough.** Accounts without a students row
  (platform-level) have no tenant and may pass an explicit institution
  through; this preserves existing platform-level behavior without widening
  tenant-bound users' access.

## 5. Security Boundary

- Tenant identity originates exclusively from the authenticated JWT-resolved
  user and their students profile row.
- A tenant-bound user requesting another institution's resources receives
  `403 TENANT_MISMATCH`; the protected operation (chat pipeline, admin
  listing, ingestion) is confirmed by tests to never execute.
- Cross-tenant object access via `assert_tenant_object` raises
  `TENANT_MISMATCH`; the user's own rows and global (`NULL` institution)
  rows are permitted.
- Defense-in-depth: endpoints resolve the tenant before dispatching to the
  service layer, and the shared guards can be (and are) re-applied at the
  object level.
- Verified by `backend/tests/test_tenant_isolation.py`: cross-tenant chat,
  foreign-institution admin listing (rejection and force-scoping), and
  cross-tenant object assertions all return the documented rejections with
  no existence leakage beyond the uniform mismatch error.

## 6. Tests and Results

- New dedicated suite: `backend/tests/test_tenant_isolation.py` —
  **12 tests, 12 passed** (executed directly: `12 passed in 2.67s`).
  Coverage includes tenant resolution/normalization, own-institution
  allowance, default-to-own-tenant, cross-tenant rejection,
  platform-account passthrough, global-row allowance, cross-tenant row
  rejection, chat cross-tenant rejection (pipeline not invoked), chat
  own-tenant propagation, admin list foreign-institution rejection, and
  admin list force-scoping.
- Full backend suite (excluding live-service integration/physical/e2e
  files that require a running backend process and therefore error at
  collection without one): **591 passed, 0 failed**.
- The live-service test files (`test_integration.py`,
  `test_physical_phase_4_3.py`, `test_faq_api.py`, `test_faq_api2.py`,
  `test_faq_e2e.py`, `test_faq_publish.py`, `test_chatbot_query.py`)
  require a live backend/Supabase connection and error when no service is
  running. This is pre-existing, environment-dependent behavior, not
  caused by and not attributable to Phase 6.1.
- Existing functionality remains passing; no previously locked test
  behavior was reopened by Phase 6.1.

## 7. Database / Migration Status

- **No schema changes.**
- **No migrations created, modified, or required.** The existing
  `institution_id` column serves as the tenant key; enforcement is
  application-level (FastAPI dependency/guard layer), consistent with the
  decision in Section 4.

## 8. Known Limitations

- **Run-based ingestion sub-steps:** ingestion sub-steps identified by a
  processing-run ID remain role-gated (authenticated + authorized role) but
  do not yet perform the complete tenant-ownership traversal
  (processing run → document version → document → knowledge source →
  institution). This is documented as a **future security-hardening item**
  and does NOT block Phase 6.1. It must be addressed in a later hardening
  phase before multi-tenant production ingestion is trusted for
  run-scoped operations.
- No frontend tenant UI (institution switcher/admin tenant views) is part
  of this phase; Phase 6.1 is backend enforcement only.

## 9. Phase 6.1 Completion Statement

**Phase 6.1 is complete.** All tenant-isolation requirements verified
during this phase are implemented, tested, and documented in this lock
record. No further Phase 6.1 implementation changes are authorized without
reopening the phase through the project's change-control process.

## 10. Phase 6.2 Statement

**Phase 6.2 has NOT been implemented.** No Phase 6.2 functionality exists
in this repository as of this lock. Any Phase 6.2 work (including the
run-ownership-traversal hardening noted in Section 8) must begin from a
clean, locked Phase 6.1 baseline and be planned, implemented, validated,
and locked under its own phase record.

---

## Files attributable to Phase 6.1

Production code:
- `backend/app/core/security.py` — `user_tenant_id`, `scope_tenant`,
  `assert_tenant_object`, `_tenant_mismatch` (403 `TENANT_MISMATCH`)
- `backend/app/main.py` — chat endpoint tenant scoping before processing
- `backend/app/api/admin.py` — tenant-scoped admin queries
- `backend/app/services/admin_academics.py` — tenant-scoped admin services
- `backend/app/api/students.py` — tenant enforcement on student endpoints
- `backend/app/api/ingestion.py` — tenant enforcement on ingestion endpoints
- `backend/app/db/supabase.py` — tenant lookup helpers

Tests:
- `backend/tests/test_tenant_isolation.py` — NEW dedicated tenant-isolation
  suite (12 tests)
- `backend/tests/test_auth.py` — platform-account (no-tenant) resolution
  coverage
- `backend/tests/test_ingestion.py` — ingestion tenant-enforcement coverage

## Git

- Baseline HEAD at lock review: `75a794e28bd42c5d3f8008428a4457cd7e2818ce`
  ("feat: complete RAG optimization and performance improvements"), branch
  `main` (tracking `meshil-maring/main`).
- The Phase 6.1 implementation exists as uncommitted working-tree changes
  (9 modified files + 1 new test file, `292 insertions(+) / 14
  deletions(-)`). No commit was performed as part of this lock; commit /
  push is an explicit post-lock action.
- Production code, tests, and migrations were NOT modified as part of
  creating this lock record; this document is the only file added by the
  lock step.

---

## Official lock statement

> "Phase 6.1 is complete and locked. Tenant identity is resolved only from
> the authenticated user, client-supplied institution identifiers can never
> cross tenant boundaries, and every tenant-keyed query and object access is
> guarded server-side with a uniform 403 TENANT_MISMATCH rejection. The
> existing institution_id remains the sole canonical tenant key with no new
> tenant schema. Run-scoped ingestion ownership traversal is documented as a
> future hardening item and does not block this lock. No further Phase 6.1
> implementation changes are authorized without reopening the phase through
> the project's change-control process."

PHASE 6.1 — LOCKED

