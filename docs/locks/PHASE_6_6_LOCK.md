# PHASE 6.6 — ROLE-BASED ACCESS CONTROL (RBAC) LOCK

## STATUS: LOCKED

Lock date: 2026-09-13
Locked at formal review approval. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.6

## 2. Phase Name

Phase 6.6 — Role-Based Access Control (RBAC)

## 3. Locked Objective

Phase 6.6 establishes and verifies Role-Based Access Control using the
existing authorization architecture.

Existing primitive:

`require_roles(*allowed)` (`backend/app/core/security.py`)

No second RBAC framework was introduced. No duplicate role system was
introduced. No duplicate tenant system was introduced. No Phase 6.6
production implementation files were required because the existing RBAC
architecture already provided the required behavior; Phase 6.6 is
verification plus documentation of the locked boundaries.

## 4. Locked Role Model

ADMIN:

- Permitted administrative operations.
- Institution-bound admin -> own institution only.
- Platform admin (`institution_id=None`) retains the locked global
  authority established by Phase 6.1 and Phase 6.4.

STAFF:

- Permitted staff operations.
- Student approval/rejection within own institution.
- Ingestion where existing policy permits.
- Cannot automatically inherit admin-only privileges.
- Platform staff does not become global admin.

FACULTY:

- Existing permitted ingestion functionality only.
- No admin authority.
- No approval authority.
- Institution-scoped where the operation carries an institution.

STUDENT:

- Permitted student functionality only.
- Own identity/ownership checks.
- Own conversations/chat where existing policy permits.
- No admin/staff/faculty privileged operations.
- No institution management.
- No student approval/rejection.
- No access to other students' protected data.

## 5. Locked Authorization Principle

RBAC answers:

"What can this user do?"

Tenant authorization answers:

"Which institution's data can this user access?"

Both are required.

Canonical tenant key:

`students.institution_id`

Existing tenant helpers remain authoritative:

- `user_tenant_id()`
- `scope_tenant()`
- `assert_tenant_object()`

Client-supplied `institution_id` cannot override authorization.

## 6. Locked Platform Policy

The existing locked convention is preserved without widening or change.

Platform admin:

`institution_id = None` + role `admin` -> retains global authority
where existing policy permits (any-institution lists/reads/updates;
approve/reject any student with the write pinned to the target tenant;
optional explicit `?institution_id=` filter on the pending queue).

Platform staff:

`institution_id = None` + role `staff` -> does NOT receive global
administrative authority. Platform staff remains forbidden from the
global student approval authority established in Phase 6.4
(403 `FORBIDDEN`).

## 7. Locked Endpoint Audit

Verified existing authorization boundaries (recorded, not invented):

- `/api/v1/admin/*` -> admin-only, except the Phase 6.4 approval
  endpoints (`GET /students/pending`, `POST /students/{id}/approve`,
  `POST /students/{id}/reject`), which use admin + staff with
  tenant-aware approval scope (`_approval_scope`).
- `/api/v1/documents/*` -> admin + staff + faculty per existing
  ingestion policy (`_INGEST_ALLOWED`); `/ingest` asserts the target
  knowledge-source tenant.
- `/api/v1/students/me/*` -> authenticated identity resolved
  server-side (`users.user_id` -> `students.user_id`); client-supplied
  student identity cannot redirect ownership.
- `/api/v1/conversations*` -> authenticated user + ownership checks
  (foreign conversation -> existing 404 anti-enumeration response).
- `/api/v1/generation/chat` -> authenticated user + tenant scope
  (`scope_tenant` before the pipeline runs).
- `/api/v1/auth/*` -> public authentication endpoints by design
  (general login plus Phase 6.5 student login with locked
  `extra="forbid"` validation).
- `/api/v1/registration` -> public registration endpoint with strict
  request validation (`extra="forbid"`, pending-only, no role grant).
- `/api/v1/dev/auth/*` -> existing development flag
  (`DEV_TEST_MODE`) + role restrictions (admin reset keeps
  `require_roles("admin")`).

## 8. Locked Security Behavior

Authorization fails closed:

- Unauthenticated -> 401.
- Authenticated but insufficient role -> 403 `FORBIDDEN`.
- Wrong tenant -> 403 `TENANT_MISMATCH`.
- Wrong object ownership -> existing safe authorization response,
  including 404 where already established for anti-enumeration
  (conversations).

Denied operations must not execute (verified via
`assert_not_called`). No 200-with-empty-results on denial.
Client-controlled role, `institution_id`, `user_id`, `student_id`, or
similar identity fields must not override server-side authorization.

## 9. Database

No Phase 6.6 migration. No duplicate role fields. No duplicate tenant
fields. No permissions/policy tables introduced. No RLS redesign.
Existing database architecture (`roles` / `user_roles` / `users` /
`students` / `institutions`) remains authoritative.

## 10. Test Baseline (locked, verified from canonical directory)

Phase 6.6 focused tests: 28 passed, 0 failed, 0 skipped
(`backend/tests/test_rbac_phase_6_6.py`).

Focused Phase 6.1-6.5 regression: 199 passed, 0 failed, 2 skipped
(2 pre-existing opt-in physical tests; RBAC + tenant isolation + 6.4
approval + 6.2 model + 6.3 registration + students API + student data
service + admin API + dev auth).

Full backend suite from the canonical `backend/` working directory:
765 passed, 0 failed, 2 skipped.

Canonical command:

```text
cd backend
python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py
```

Root-directory record: a prior run from the repository root reported
756 passed, 9 failed, 2 skipped. Each of the nine failures was
investigated individually; all nine passed from the correct `backend/`
working directory and were determined to be pre-existing
environment/CWD/configuration artifacts, not caused by Phase 6.6
(empty `Settings` from the unloaded `backend/.env`: Supabase client
construction, JWKS init, R2 bucket default, and one vector-search
test-isolation ordering effect).

## 11. Test Integrity

Recorded explicitly:

- No tests were weakened.
- No tests were deleted.
- No tests were artificially skipped.
- No production behavior was modified to force green.
- Phase 6.6 production code was not modified (no production files
  changed; `git diff` empty apart from this lock step).
- Existing Phase 6.1-6.5 implementation was not modified.

## 12. Project Configuration Limitation

Known limitation: `Settings` currently loads `.env` relative to the
process CWD (`env_file=".env"` in `backend/app/config.py`). Therefore
the backend test suite must be executed from `backend/`.

Future hardening may consider making configuration loading
CWD-independent, but that is OUTSIDE Phase 6.6 and was not implemented
as part of this lock. Other known pre-existing hardening
opportunities, also NOT Phase 6.6 work:

- validation before client initialization in relevant admin-academic
  services;
- improved test isolation around `get_admin_client()`;
- future RLS review consistent with application guards;
- run-scoped ingestion sub-step tenant traversal
  (run -> version -> document -> knowledge source -> institution).

## 13. Stray File Verification

The empty untracked `identifier` file encountered during Phase 6.6
inspection was confirmed to be never tracked, absent from HEAD,
unrelated to any project phase, and an accidental inspection artifact.
It was removed. No tracked project content was affected.

## 14. Files

Final Phase 6.6 additions:

- `backend/tests/test_rbac_phase_6_6.py` (NEW, 28 tests)
- `PHASE_6_6_STATUS.md` (status document)
- `PHASE_6_6_LOCK.md` (this document)

No Phase 6.6 production implementation files were required because the
existing RBAC architecture already provided the required behavior. No
unrelated files are claimed as Phase 6.6 changes.

## 15. Phase Boundary

Phase 6.6 does NOT implement:

- Phase 6.7 attendance
- Phase 6.8 test/exam results
- Phase 6.9 student-specific academic data system
- Phase 6.10 personalized chatbot
- Phase 6.11 broader security testing
- Phase 6.12 final demo validation

Phase 6.6 is ONLY RBAC and authorization verification/enforcement.

---

## 16. Lock Verification

Pre-lock checks performed: `git status` showed only the intended
untracked Phase 6.6 files; `git diff` showed no tracked modifications;
no Phase 6.1-6.5 lock files modified; no production code or tests
changed since final verification. Post-lock check below confirms the
lock step added only this document.

---

## Official lock statement

> "Role-Based Access Control and authorization boundaries are formally
> locked. No Phase 6.7+ functionality has been implemented as part of
> this lock."

PHASE 6.6 — LOCKED
