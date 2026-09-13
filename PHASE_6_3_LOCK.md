# PHASE 6.3 — STUDENT REGISTRATION LOCK

## STATUS: LOCKED

Lock date: 2026-09-12
Locked at final verification completion. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.3

## 2. Phase Name

Phase 6.3 — Student Registration (Public Self-Service, Pending-Only)

## 3. Final Architecture

Phase 6.3 adds a public self-service registration flow on top of the
LOCKED Phase 6.1/6.2 foundations. It creates no second user table, no
second authentication architecture, and no new tenant key. The final
registration flow:

- Endpoint: `POST /api/v1/registration` (`backend/app/api/registration.py`,
  prefix `/registration` under `/api/v1`), public/unauthenticated.
- Service: `backend/app/services/student_registration.py`
  (`register_student`, `StudentRegistrationRequest`,
  `RegistrationResponse`).
- Chain preserved exactly as locked:

```text
auth.users (Supabase GoTrue)
     |  users.auth_user_id
public.users
     |  students.user_id
students
     |  students.institution_id
institutions
```

- Institution: client-supplied `institution_id` only; must exist and be
  active (`is_active`), else 404 `INSTITUTION_NOT_FOUND` / 403
  `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS`. No institution write exists
  on this path.
- Academic identity: registration requires at least one REAL identifier
  (`register_number` OR `university_roll_number`, else 422
  `IDENTIFIER_REQUIRED`); `students.student_number` is derived
  server-side from that identifier. No synthetic placeholder exists.
- Approval: every created profile is inserted with hardcoded
  `approval_status='pending'` (`PENDING` constant), never read from the
  client; no path produces `approved`/`rejected`.
- Auth boundary: password goes ONLY to the existing
  `client.auth.sign_up` (Supabase Auth GoTrue) — never stored, hashed,
  logged, echoed, or persisted in any application table.
- Failure handling: GoTrue cannot join the PostgREST transaction, so
  partial failures are compensated best-effort (users-insert failure
  deletes the fresh auth account; students-insert failure deletes the
  fresh users row + auth account), documented in the service docstring.


## 4. Registration Request / Response Contract

Request (`StudentRegistrationRequest`, `extra="forbid"` — `role`,
`roles`, `approval_status`, `is_admin`, institution-creation keys, and
any other extra field rejected with 422 before any service call):

| Field | Required | Notes |
| --- | --- | --- |
| institution_id | ✔ | existing, active institution only |
| email | ✔ | normalized lowercase/trimmed |
| password | ✔ | min 6 chars; GoTrue only, never stored |
| first_name / last_name | ✔ | non-blank (public.users NOT NULL) |
| register_number | at least one of the two | trimmed; blank → None |
| university_roll_number | at least one of the two | trimmed; blank → None |
| enrollment_date | ✘ | defaults to today |

Response (201): `{message, student_id, institution_id, email,
approval_status='pending'}` — clearly pending approval; no password,
no tokens, no roles, no other students.

## 5. `student_number` Derivation (Review Decision — No Placeholder)

`students.student_number` is NOT NULL with `btrim <> ''` (Admin-1) and
`UNIQUE (institution_id, student_number)` (Phase 6.2); it is the
institution-assigned academic number consumed by CSV result upload and
admin list ordering. The review rejected both a constant placeholder
(second numbers-less registration would violate the UNIQUE key) and a
random token (masquerades as a real academic number). Nullable was
rejected (schema migration on a locked column, weakens CHECK/UNIQUE,
NULLs leak into CSV resolution). Final rule: require one real
identifier, derive `student_number` from it (register number, else
university roll number). Proven by
`test_missing_both_identifiers_rejected_no_synthetic_number` (zero
auth/DB side effects), `test_blank_identifiers_treated_as_missing`, and
`test_roll_number_only_becomes_student_number`.

## 6. Identity Uniqueness Strategy

- Same institution → 409 each: `EMAIL_ALREADY_REGISTERED`,
  `REGISTER_NUMBER_ALREADY_REGISTERED`,
  `ROLL_NUMBER_ALREADY_REGISTERED` (all duplicate lookups carry the
  requested `institution_id`).
- Cross-institution → Phase 6.2 institution-scoped uniqueness holds
  (College A `register_number = 1001`, College B `register_number =
  1001` coexist).
- Existing `public.users` without a student profile → 409
  `EMAIL_ALREADY_REGISTERED` (no duplicate user created).
- Existing student profile for that account → 409
  `STUDENT_ALREADY_REGISTERED` (no duplicate profile created).
- Existing GoTrue auth account conflict → 409
  `EMAIL_ALREADY_REGISTERED`.

## 7. Security Boundary

- Public endpoint accepts ONLY the whitelisted identity fields;
  privilege escalation is impossible by construction (`extra="forbid"`
  + hardcoded `pending` + no role assignment).
- A registrant cannot become admin/staff, choose a role, set approval
  state, read or modify another student, create institutions, or cross
  tenant boundaries (registration for A never touches B —
  test-enforced).
- Tenant authority unchanged: Phase 6.1 server-side tenant resolution
  untouched; registration scopes everything to the validated
  `institution_id`.

## 8. Migration Status

No migration required or created. Phase 6.2 already provides
`students.email / register_number / university_roll_number /
approval_status / institution_id` plus institution-scoped uniqueness.
No schema, constraint, index, or data change in this phase.

## 9. Full Test-Suite Results

- **Phase 6.3 suite**
  (`backend/tests/test_student_registration_phase_6_3.py`):
  **26 passed, 0 failed** (mocked Supabase client; hermetic).
- **Focused run** (registration + students_api + student_data_service +
  student_model_phase_6_2 + tenant_isolation + auth + dev_auth):
  **116 passed, 2 skipped, 0 failed**.
- **Full backend suite** (`pytest tests/`):
  **655 passed, 5 skipped, 0 failed**
  (629/5 baseline + 26 new; the 5 skipped are pre-existing opt-in
  physical tests).

## 10. Git Verification

- Phase 6.3 touched ONLY (verified via `git status --short`,
  path-limited `git diff --numstat`, and checkpoint-commit comparison):
  - `backend/app/services/student_registration.py` (new)
  - `backend/app/api/registration.py` (new)
  - `backend/tests/test_student_registration_phase_6_3.py` (new)
  - `backend/app/main.py` (router include only: 12 insertions,
    2 deletions — the remaining hunk is pre-existing Phase 6.1
    `scope_tenant` work, untouched since before this session)
  - `PHASE_6_3_STATUS.md` + `PHASE_6_3_LOCK.md` (docs)
- The other modified files in `git status` (admin.py, ingestion.py,
  students.py, security.py, supabase.py, admin_academics repo/service,
  test_auth.py, test_ingestion.py, PHASE_6_1/6_2 docs, 6.2 migration,
  test_tenant_isolation.py) are **pre-existing Phase 6.1/6.2 work,
  uncommitted before Phase 6.3 began** — NOT Phase 6.3 changes and not
  modified by this phase.
- No unrelated production files changed; no temporary inspection files
  remain.

## 11. Known Limitations / Remaining Risks

- Numbers-less self-registration is intentionally rejected (422
  `IDENTIFIER_REQUIRED`); Phase 6.4/6.5 may tighten or relax
  requiredness deliberately.
- GoTrue + PostgREST compensation is best-effort; a crash between steps
  can leave an auth-only account (re-registration reports 409; the
  students-based Phase 6.4 queue is unaffected).
- Email confirmation stays inside Supabase Auth.
- Approval gating (`approval_status='approved'` → login allowed) is
  Phase 6.4/6.5 behavior; this phase only ever writes `pending`.

## 12. Explicit Phase 6.4+ Exclusions (NOT implemented)

Admin/staff approval workflow endpoints and UI; student login (email /
register-number / university-roll-number); password handling beyond
GoTrue signup; attendance; test/exam results; personalized or
student-specific chatbot context; new RBAC system; RLS policies;
approval-queue admin endpoints; frontend changes. The only
approval-related behavior is `registration → pending`.

---

# PHASE 6.3 — LOCKED ✅
