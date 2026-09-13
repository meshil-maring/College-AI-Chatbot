# PHASE 6.3 — STUDENT REGISTRATION STATUS

## STATUS: COMPLETE — READY FOR REVIEW (not locked)

Status date: 2026-09-12
Baseline: PHASE_6_2_STATUS.md / PHASE_6_2_LOCK.md (LOCKED)
No LOCK record is created by this step; locking requires separate review per
project change-control convention.

---

## 1. Phase Number / Name

Phase 6.3 — Student Registration (public self-service, pending-only).

## 2. Objective (from phase brief)

Allow a prospective student to submit a registration request for a specific
institution, creating the account records while leaving the student at
`approval_status = pending`. Registration must NOT approve the student —
approval belongs exclusively to Phase 6.4.

## 3. Architecture Inspected (before implementing)

- `public.users`: link row `auth_user_id → user_id`; email globally unique.
- Supabase Auth: GoTrue owns credentials (`backend/app/api/auth.py`
  signup/login via `client.auth.sign_up` / `sign_in_with_password`).
- JWT: `backend/app/core/security.py` (`verify_jwt`, `get_current_user`).
- Student repository: `backend/app/repositories/admin_academics.py`
  (identity lookups `get_student_by_email/register_number/
  university_roll_number/user_id`, all institution-scoped per 6.2).
- Student service: `backend/app/services/admin_academics.py`
  (admin provisioning defaults to `approved` — self-registration does not
  reuse that path).
- Student APIs: `backend/app/api/students.py`, `backend/app/api/admin.py`.
- Schemas/errors: Pydantic v2 models; `AppError` + handler with
  `{error: {code, message}}` bodies.
- Locked relationship preserved exactly:

```text
auth.users (Supabase GoTrue)
     |  users.auth_user_id
public.users
     |  students.user_id
students
     |  students.institution_id
institutions
```

No second user/authentication architecture was created.

## 4. Registration Flow (as built)

```text
Submit registration (public, unauthenticated)
  -> fail fast: require register_number OR university_roll_number (422
     IDENTIFIER_REQUIRED — no synthetic student_number is fabricated)
  -> validate institution (exists + is_active)
  -> existing-account check (public.users by email, then student link)
  -> validate identity fields (institution-scoped duplicates)
  -> create auth account via EXISTING sign_up (password only to GoTrue)
  -> create public.users link row (compensate auth on failure)
  -> create students profile approval_status='pending'
     (compensate users row + auth on failure)
  -> 201 {message, student_id, institution_id, email,
          approval_status='pending'}
```

- Endpoint: `POST /api/v1/registration`
  (`backend/app/api/registration.py`, prefix `/registration`).
- Service: `backend/app/services/student_registration.py`.
- `students.student_number` (NOT NULL, non-blank, UNIQUE per institution;
  the institution-assigned academic number consumed by CSV result upload
  and admin list ordering) is derived server-side from a REAL submitted
  identifier: register number, else university roll number. The review
  decision (see PHASE_6_3_STATUS §16 addendum in the final report) was
  to REQUIRE at least one identifier (422 `IDENTIFIER_REQUIRED`) rather
  than fabricate `STU-pending`: a constant placeholder would collide
  under the UNIQUE key on the second numbers-less registration, and a
  random token would masquerade as a real academic number. No extra
  client `student_number` field was added.
- GoTrue cannot join the PostgREST transaction, so partial failures are
  compensated best-effort (documented in the service docstring).

## 5. Files Changed

- NEW `backend/app/services/student_registration.py`
- NEW `backend/app/api/registration.py` (public POST, 201)
- EDIT `backend/app/main.py` (router include under `/api/v1`)
- NEW `backend/tests/test_student_registration_phase_6_3.py` (24 tests)
- NEW `PHASE_6_3_STATUS.md` (this file)

## 6. Database Changes

None. Phase 6.2 already provides `students.email / register_number /
university_roll_number / approval_status / institution_id` plus
institution-scoped uniqueness. No migration created.


## 7. Authentication Integration

- Password goes ONLY to `client.auth.sign_up` (same call as
  `POST /api/v1/auth/signup`). Never stored, hashed, logged, echoed, or
  persisted in any application table (asserted on both inserts + body).
- Duplicate auth emails (`AuthApiError` 4xx email_exists / already-*)
  map to `409 EMAIL_ALREADY_REGISTERED` under the `AppError` convention.
- Response never contains password, tokens, roles, or other students.

## 8. Approval Behavior

- Every profile is inserted with hardcoded `approval_status='pending'`
  (`PENDING` constant), never read from the client.
- No path in this phase can produce `approved`/`rejected`.
- Message: "Registration submitted. Your account is pending approval."

## 9. Duplicate Handling

- Same institution: duplicate email / register number / roll number
  each → 409 with a dedicated code.
- Cross-institution: lookups always carry the requested
  `institution_id`, so `register_number = 1001` at College A and B
  coexist (Phase 6.2 scoping; scoped-lookup test asserts this).
- Existing `public.users` without profile → 409, no duplicate user.
- Existing student profile → 409, no duplicate profile.

## 10. Security

- Request model `extra="forbid"`: `role`, `roles`, `approval_status`,
  `is_admin`, institution-creation keys → 422 before any service call.
- No role granted; no elevated access; no other student's data;
  no institution write on this path.

## 11. Tests (26, mocked/hermetic)

Success/pending/institution/identity; roll-number-only derivation;
numbers-less and blank-numbers both → 422 `IDENTIFIER_REQUIRED` with
zero auth/DB side effects; invalid (404) + inactive (403) institution;
3 same-institution duplicates (409); scoped lookups; existing
user/student/auth (409); 7 privilege-escalation 422s; short password
422; password secrecy; 2 compensation tests; tenant-A-never-touches-B.

## 12. Full Suite

```text
655 passed, 5 skipped, 0 failed
```

(629/5 baseline + 26 Phase 6.3 tests; tenant, student, auth suites
included.)

## 13. Git Diff (summary)

- `backend/app/api/registration.py` (new)
- `backend/app/services/student_registration.py` (new)
- `backend/app/main.py` (router include)
- `backend/tests/test_student_registration_phase_6_3.py` (new)
- `PHASE_6_3_STATUS.md` (new)

## 14. Known Limitations

- Email confirmation stays inside Supabase; same 201 pending either way.
- GoTrue + PostgREST compensation is best-effort; a crash between steps
  can leave an auth-only account (re-registration reports 409; the
  students-based Phase 6.4 queue is unaffected).
- Numbers-less self-registration is rejected (422 `IDENTIFIER_REQUIRED`);
  Phase 6.4/6.5 can tighten or relax requiredness deliberately.

## 15. Scope Verification (excluded)

No approval workflow, no student login, no attendance/results/chatbot/
RBAC/RLS/authorization redesign. Only `registration → pending`.

## 16. Review Addendum — STU-pending Decision (review item 1)

Finding: the original `STU-pending` fallback was UNSAFE and was removed.

- `students.student_number` is NOT NULL with `btrim <> ''` (Admin-1)
  and `UNIQUE (institution_id, student_number)` (6.2); it is the
  institution-assigned academic number consumed by CSV result upload
  (`student_number` → student resolution) and admin list ordering.
- A constant `STU-pending` would violate "no fake duplicate academic
  identifiers": the second numbers-less registration at the same
  institution fails the UNIQUE key (or worse, one row silently owns a
  fake shared number).
- Option A (nullable student_number) was rejected: it needs a schema
  migration touching a locked NOT NULL column, weakens the CHECK/UNIQUE
  semantics Phases 6.2/6.4 rely on, and lets NULLs flow into CSV
  resolution.
- Option B (random unique temp id) was rejected: a random token
  masquerades as a real academic number to upload/listing/approval.
- Chosen: require at least one REAL identifier (register_number OR
  university_roll_number; 422 `IDENTIFIER_REQUIRED`), then derive
  `student_number` from it. No migration, no placeholder, no new client
  field, no fake duplicates, existing rows/provisioning untouched.
  Proven by `test_missing_both_identifiers_rejected_no_synthetic_number`
  (zero auth/DB side effects), `test_blank_identifiers_treated_as_missing`,
  and `test_roll_number_only_becomes_student_number`.
