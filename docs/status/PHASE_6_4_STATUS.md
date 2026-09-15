# PHASE 6.4 — ADMIN/STAFF STUDENT APPROVAL STATUS

## STATUS: COMPLETE — READY FOR REVIEW (not locked)

Status date: 2026-09-12
Baseline: PHASE_6_1/6_2/6_3 LOCKED. Locking needs separate review.

## 1. Objective

Authorized approvers review Phase 6.3 `pending` registrations:

```text
pending → admin/staff review → approved OR rejected
```

Nothing else: no login, attendance, results, chatbot, RBAC, or RLS changes.

## 2. Architecture inspected

- RBAC: single `require_roles(*allowed)` in `core/security.py`
  (401 via `get_current_user`, else 403 `FORBIDDEN`). No second RBAC.
- Roles: `admin` guards `/admin/*`; `staff` already exists (ingestion uses
  `require_roles("admin", "staff", "faculty")`). No new role added.
- Chain preserved: GoTrue → `public.users` → `students.user_id` →
  `students.institution_id` → `institutions`.
- Tenant: `institution_id` canonical key; `user_tenant_id` server-side;
  mismatch → 403 `TENANT_MISMATCH`. `get_user_by_auth_id` already joins
  roles + `students(institution_id)`.
- Extended additively: `repositories/admin_academics.py` (reads) +
  `services/admin_academics.py` (writes) + `api/admin.py` (routes).
  Existing CRUD untouched.
- Phase 6.2 already gives `approval_status` + CHECK + the
  `(institution_id, approval_status)` index. No migration needed.
- Audit: existing `admin_audit_log` + `record_admin_action` reused.
- Errors: `AppError` → `{error: {code, message}}`.


## 3. Authorization (OPTION A — platform policy, review decision)

- New `_APPROVAL = require_roles("admin", "staff")` in `api/admin.py` —
  same primitive, existing role names. Staff allowed because the role
  exists and the brief lists admin/staff as expected approvers.
- Role model (explicit, tested):
  * **Platform-level ADMIN** (no students profile → tenant None):
    GLOBAL approval authority — approve/reject any student, and the
    pending list may be global or filtered by an explicit
    `?institution_id=` (Phase 6.1 platform passthrough convention;
    the existing admin CRUD already lets a platform admin read/update
    any student incl. `approval_status` via `PATCH /students/{id}`).
  * **Institution admin / institution staff** (tenant-bound): strictly
    their OWN institution; a foreign `?institution_id` → 403
    `TENANT_MISMATCH`; cross-tenant target → 403 `TENANT_MISMATCH`.
  * **Platform-level STAFF** (tenant None, staff role): 403 `FORBIDDEN` —
    a tenant-less account never gains approval authority without the
    platform-admin role (this closes the escalation surface; an earlier
    draft fell back to the target tenant for any tenant-less caller and
    was tightened during this review).
  * Students / faculty / unauthenticated: 403 / 401 (standard errors).
- Unauthenticated → 401; student/faculty/other → 403 `FORBIDDEN` (tested).
- All other admin endpoints stay `admin`-only (unchanged).

## 4. Tenant isolation

- Institution-bound approvers: acting institution ONLY from
  `user_tenant_id`; a foreign `?institution_id=B` → 403 `TENANT_MISMATCH`
  (standard Phase 6.1 rejection, tested; never silently rewritten).
- Target tenant checked BEFORE state (no leak); mismatch → 403
  `TENANT_MISMATCH`. List query is
  `WHERE institution_id=<tenant> AND approval_status='pending'`
  (platform admins may omit the tenant filter deliberately — OPTION A).

## 5. Endpoints (no duplicates, existing conventions)

```text
GET  /api/v1/admin/students/pending
POST /api/v1/admin/students/{student_id}/approve   (pending → approved)
POST /api/v1/admin/students/{student_id}/reject    (pending → rejected)
```

- Declared BEFORE `/students/{student_id}` so `/pending` matches.
- Bodies take NO fields: body `institution_id`/`role`/`approval_status`
  inert by construction (tested). Only approval state changes.
- Rejection preserves auth + `public.users` + students row (`rejected`).
- Minimal `STUDENT_APPROVAL_COLUMNS` projection; no secrets (tested).

## 6. State machine (strict): pending → approved | rejected

- Non-pending → 409 `STUDENT_NOT_PENDING` (all 4 combos tested).
- Unknown → 404 `STUDENT_NOT_FOUND`. No re-review by design.

## 7. Audit: existing `admin_audit_log` reused

- Each mutation writes `student.approve` / `student.reject` with
  server-resolved `actor_user_id` (tested). When = existing timestamps.
- No approver column added to `students` (rejected: locked-table migration
  for data the audit log already holds).

## 8. Concurrency: conditional write

- `UPDATE … WHERE student_id=X AND institution_id=<tenant> AND
  approval_status='pending'`. Loser re-reads: gone → 404, done → 409.

## 9. Database changes: NONE (Phase 6.2 sufficient). Data preserved.

## 10. Tests: 36 passed (`test_student_approval_phase_6_4.py`)

Auth (401/403/admin/staff), tenant (A-only list, foreign query 403,
cross-tenant admin/staff approve+reject 403, tenant-before-state), list
filters, approve/reject, 404, conditional write, 4 invalid transitions +
API 409, body tampering ×2, stale/double → 409, audit ×2, no-leak, and the
OPTION A platform section: platform admin approves A / rejects B (service
+ endpoint, write pinned to target tenant), global + filtered platform
listing, platform staff 403 (approve/reject/list), tenant-less student 403,
institution staff cross-tenant 403 ×2, own-institution query accepted.

## 11. Full suite: 691 passed, 5 skipped, 0 failed

(655/5 Phase 6.3 baseline + 36 new; 5 skipped = pre-existing opt-in
physical. Must run from `backend/` so `backend/.env` loads — repo-root
runs fail 4 unrelated tests on missing env, pre-existing, unrelated to
this phase. Focused run: 184 passed, 2 skipped, 0 failed.)

## 12. Files changed (Phase 6.4 only)

- `backend/app/repositories/admin_academics.py` (+queue helpers/projection;
  list query tenant filter optional for the platform-admin passthrough)
- `backend/app/services/admin_academics.py` (+approve/reject/list with
  documented OPTION A scope semantics)
- `backend/app/api/admin.py` (+`_APPROVAL`, `_approval_scope` policy
  resolver, 3 routes)
- `backend/tests/test_student_approval_phase_6_4.py` (new, 36 tests)
- `PHASE_6_4_STATUS.md` (this file)

## 13. Known limitations

Platform STAFF (tenant-less) get 403 by design; platform admins see the
global queue unless filtered. No re-review, no notifications, no bulk ops,
limit/offset only.

## 14. Exclusions (NOT implemented)

Login (any form), passwords, attendance, results, chatbot context, new
RBAC, RLS, final security/demo, frontend. Only the approval queue above.
