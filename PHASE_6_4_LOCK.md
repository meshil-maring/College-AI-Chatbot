# PHASE 6.4 — ADMIN/STAFF STUDENT APPROVAL LOCK

## STATUS: LOCKED

Lock date: 2026-09-12
Locked at final authorization-review completion. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.4

## 2. Phase Name

Phase 6.4 — Admin/Staff Student Approval (Tenant-Safe Review Workflow)

## 3. Final Implementation State

Phase 6.4 implements the tenant-safe admin/staff approval workflow on top of
the LOCKED Phase 6.1/6.2/6.3 foundations. The verified final state:

- Endpoints (existing `/admin` router conventions, `backend/app/api/admin.py`):
    - `GET  /api/v1/admin/students/pending` — approval queue
    - `POST /api/v1/admin/students/{student_id}/approve` — pending → approved
    - `POST /api/v1/admin/students/{student_id}/reject` — pending → rejected
  All three declared BEFORE `GET /students/{student_id}` so the literal
  `/students/pending` route matches first.
- Service layer (`backend/app/services/admin_academics.py`):
  `list_pending_approvals`, `approve_student`, `reject_student` (+ private
  helpers `_approval_tenant_mismatch`, `_resolve_approval_target`,
  `_conditional_approval_write`).
- Repository layer (`backend/app/repositories/admin_academics.py`):
  `STUDENT_APPROVAL_COLUMNS` (minimal projection), `list_pending_students`,
  `get_student_for_approval`, `set_student_approval_status`.
- Authorization: `_APPROVAL = require_roles("admin", "staff")` plus the
  `_approval_scope` policy resolver in `api/admin.py`.
- Existing student CRUD, Phase 6.1 tenant primitives, Phase 6.2 identity
  model, and Phase 6.3 registration are untouched.

## 4. Architecture Decision

- **No second RBAC system.** The existing `require_roles()` primitive
  (`backend/app/core/security.py`) is reused with the EXISTING `admin` and
  `staff` role names (`staff` already existed — ingestion uses
  `require_roles("admin", "staff", "faculty")`). No new role was created.
- **No second tenant mechanism.** `institution_id` remains the canonical
  tenant key (Phase 6.1). Acting tenant is resolved ONLY server-side via
  `user_tenant_id(current_user)` (authenticated user → students profile).
  The `approval_status` column from Phase 6.2 is reused as-is.
- **PLATFORM POLICY — OPTION A (explicit review decision, not silent):**
  platform-level accounts keep the locked Phase 6.1 convention (platform
  accounts are unrestricted; `test_platform_admin_can_list_any_institution`
  already proved platform admins read any institution; the existing admin
  CRUD already lets a platform admin change any student's `approval_status`
  via `PATCH /students/{id}`). A stricter policy would have required
  reopening locked Phase 6.1 semantics.
- **Escalation tightening:** an earlier draft let ANY tenant-less caller
  fall back to the target tenant; the locked behavior restricts global
  approval authority to platform-level ADMINS only (see §5).

## 5. Approval Authorization (final, tested)

| Caller | Role | Tenant | List pending | Approve/Reject |
| --- | --- | --- | --- | --- |
| Platform Admin | admin | NULL | global (optional explicit `?institution_id=` filter) | any institution (write pinned to target's institution) |
| Institution Admin | admin | bound | own institution only | own institution only |
| Institution Staff | staff | bound | own institution only | own institution only |
| Platform Staff | staff | NULL | — | 403 FORBIDDEN (never global) |
| Student | student | any | 403 FORBIDDEN | 403 FORBIDDEN |
| Faculty | faculty | any | 403 FORBIDDEN | 403 FORBIDDEN |
| Unauthenticated | — | — | 401 | 401 |

- All other existing admin endpoints remain `admin`-only (unchanged).

## 6. Tenant Security Boundary

- Client-supplied `institution_id` can NEVER override server-side tenant
  resolution: a foreign `?institution_id` from a tenant-bound approver is
  rejected with 403 `TENANT_MISMATCH` (standard Phase 6.1 behavior; an
  own-institution query is accepted). Approval/rejection POST bodies accept
  NO fields, so `institution_id` / `role` / `approval_status` tampering is
  inert by construction — the transition target is hardcoded per endpoint
  and the scope comes only from `_approval_scope(current_user)`.
- Institution-bound users cannot access foreign students: the target
  student's `institution_id` is compared against the authenticated tenant
  BEFORE approval-state validation (no cross-tenant state leak); mismatch →
  403 `TENANT_MISMATCH` ("This resource belongs to a different institution").
- Platform-admin global behavior is explicitly documented (code comments,
  service docstrings, `PHASE_6_4_STATUS.md`) and test-enforced.

## 7. Approval State Machine (strict)

```text
pending → approved
pending → rejected
```

- Only a currently-`pending` student transitions; the conditional write
  requires `approval_status = 'pending'` at UPDATE time.
- Invalid transitions (`approved→approved`, `approved→rejected`,
  `rejected→approved`, `rejected→rejected`) → 409 `STUDENT_NOT_PENDING`
  (all four combos tested). No re-review transitions exist (no documented
  business requirement; any future re-review must be a separate phase).
- Unknown student → 404 `STUDENT_NOT_FOUND`.
- ONLY `approval_status` is modified. No unrelated updates, no arbitrary
  client fields, no role grants.

## 8. Rejection Semantics

Rejection preserves the student record — nothing is deleted:
- Supabase Auth (GoTrue) account preserved
- `public.users` row preserved
- `students` row preserved with `approval_status = 'rejected'`
(test-enforced: zero delete calls on the rejection path).

## 9. Audit Behavior

- Existing `admin_audit_log` + `record_admin_action` reused via the
  existing `_record_audit` helper: `student.approve` / `student.reject` on
  `students`, server-resolved `actor_user_id`, `record_data`
  `{"approval_status": "approved" | "rejected"}`, `performed_at` timestamp.
- No new approver column was added to `students` (deliberate: a
  locked-table migration for data the audit log already holds was evaluated
  and rejected).
- "Who" = `actor_user_id`; "when" = existing `updated_at`/`performed_at`.

## 10. Concurrency Behavior

- Conditional update (repository `set_student_approval_status`):
  `UPDATE students SET approval_status = <new> WHERE student_id = X AND
  institution_id = <scope> AND approval_status = 'pending'`.
- The loser of a race re-reads: student gone → 404 `STUDENT_NOT_FOUND`;
  already processed → 409 `STUDENT_NOT_PENDING`. Stale approve-after-reject
  and double-approve are both tested. No overengineering beyond the
  existing PostgREST chain pattern.

## 11. Data Protection

- Responses use the minimal `STUDENT_APPROVAL_COLUMNS` projection. Students
  rows carry no credentials; no passwords, access tokens, refresh tokens,
  or internal secrets are ever stored, logged, or echoed (test-enforced).

## 12. Database Changes

NONE. Phase 6.2 already provides `students.approval_status`
(`pending|approved|rejected`, CHECK-constrained, default `pending`) and the
`idx_students_institution_approval` index backing the queue query. No
migration was created; existing student data preserved untouched.

## 13. Physical / Full Test Results

- **Phase 6.4 suite** (`backend/tests/test_student_approval_phase_6_4.py`):
  **36 passed, 0 failed** (hermetic, mocked Supabase client).
- **Focused suite** (6.4 + tenant_isolation + registration_6_3 +
  student_model_6_2 + admin_api + auth + students_api +
  student_data_service + admin_academics service/repository):
  **184 passed, 2 skipped, 0 failed**.
- **Full backend suite** (`pytest tests/` from `backend/`):
  **691 passed, 5 skipped, 0 failed**
  (655/5 Phase 6.3 baseline + 36 new; the 5 skipped are pre-existing opt-in
  physical tests). NOTE: runs must start in `backend/` so `backend/.env`
  loads; repo-root runs fail 4 pre-existing unrelated tests on missing env
  (verified pre-existing by stashing all Phase 6.4 changes).

## 14. Git Verification

Phase 6.4 touched ONLY (additive; verified against the working tree):
- `backend/app/api/admin.py` — `_APPROVAL`, `_approval_scope`, 3 approval
  routes + header comment block (no existing endpoint changed)
- `backend/app/services/admin_academics.py` — approval service functions
- `backend/app/repositories/admin_academics.py` — approval queue helpers
- `backend/tests/test_student_approval_phase_6_4.py` — NEW (36 tests)
- `PHASE_6_4_STATUS.md` + `PHASE_6_4_LOCK.md` (docs)

Pre-existing uncommitted Phase 6.1/6.2/6.3 work (pre-6.4 hunks of admin.py/
ingestion.py/students.py/security.py/supabase.py/main.py, test_auth.py,
test_ingestion.py, the 6.2 migration, registration files, prior lock docs)
was NOT modified or reset by this phase. Production code and tests were NOT
modified as part of creating this lock record; this document is the only
file added by the lock step.

## 15. Known Limitations

- Platform STAFF (tenant-less) are 403 by design; only platform ADMINS hold
  global authority.
- Platform admins see the global pending queue unless they pass an explicit
  `?institution_id=` filter.
- No re-review transitions, no decision notifications, no bulk
  approve/reject; listing pagination is limit/offset only.
- No approver column on `students` (audit log owns actor identity).

## 16. Explicit Phase 6.5+ Exclusions (NOT implemented)

Student login; email login; register-number login; university-roll-number
login; password authentication changes; attendance; test/exam results;
personalized chatbot; student-specific chatbot access; new RBAC; Supabase
RLS; final security phase; final demo validation; frontend changes. The
only approval behavior in this phase is
`pending → admin/staff review → approved | rejected`.

## 17. Phase 6.5 Statement

**Phase 6.5 has NOT been implemented.** No Phase 6.5 functionality exists in
this repository as of this lock. Any Phase 6.5 work must begin from a
clean, locked Phase 6.4 baseline and be planned, implemented, validated,
and locked under its own phase record.

---

## Official lock statement

> "Phase 6.4 is complete and locked. Approval is restricted to the existing
> admin and staff roles via the existing require_roles primitive, with a
> strict pending → approved | rejected state machine enforced by conditional
> pending-only, tenant-scoped updates. Institution-bound approvers are
> strictly limited to their own institution with 403 TENANT_MISMATCH on any
> foreign institution or student; platform-level admins hold explicitly
> documented and tested global authority; tenant-less staff accounts are
> forbidden. Rejection preserves all records, every decision is written to
> the existing admin_audit_log, and no database migration was required.
> Phase 6.5 functionality does not exist in this repository."

PHASE 6.4 — LOCKED ✅

## 11. Data Protection

- Responses use the minimal `STUDENT_APPROVAL_COLUMNS` projection. Students
  rows carry no credentials; no passwords, access tokens, refresh tokens,
  or internal secrets are ever stored, logged, or echoed (test-enforced).

## 12. Database Changes

NONE. Phase 6.2 already provides `students.approval_status`
(`pending|approved|rejected`, CHECK-constrained, default `pending`) and the
`idx_students_institution_approval` index backing the queue query. No
migration was created; existing student data preserved untouched.

  `user_tenant_id(current_user)` (authenticated user → students profile).
  The `approval_status` column from Phase 6.2 is reused as-is.
- **PLATFORM POLICY — OPTION A (explicit review decision, not silent):**
  platform-level accounts keep the locked Phase 6.1 convention (platform
  accounts are unrestricted; `test_platform_admin_can_list_any_institution`
  already proved platform admins read any institution; the existing admin
  CRUD already lets a platform admin change any student's `approval_status`
  via `PATCH /students/{id}`). A stricter policy would have required
  reopening locked Phase 6.1 semantics.
- **Escalation tightening:** an earlier draft let ANY tenant-less caller
  fall back to the target tenant; the locked behavior restricts global
  approval authority to platform-level ADMINS only (see §5).
