# PHASE 6.13.5 — Student, Faculty & Staff Registration

## 1. Files Changed

### New Files
- `backend/app/api/users.py` — public `POST /api/v1/users/register` wiring (thin layer, delegates to service)
- `backend/app/schemas/users.py` — `UserRegistrationRequest` / `UserRegistrationResponse` (Literal type, `extra="forbid"`)
- `backend/app/services/user_registration.py` — unified orchestration (reuses Phase 6.3 + 6.13 primitives, no new auth provider)
- `backend/tests/test_user_registration_phase_6_13_5.py` — 39 focused tests (mocked Supabase clients, no live services)

### Modified Existing Files (reused, not rewritten)
- `backend/app/main.py` — registers `users_router` at `/api/v1` (one include line; existing routers untouched)

### Deliberately Untouched (per scope restrictions)
- `backend/app/services/student_registration.py` — student helpers reused as-is (no rewrite)
- `backend/app/services/tenancy.py` — `get_institution_by_code`, `_assert_institution_active`, `PENDING` reused as-is
- `backend/app/repositories/tenancy.py` — `get_institution_by_code`, `insert_membership_request` reused as-is
- `backend/app/repositories/admin_academics.py` — student identity lookups reused as-is
- `authorization.py`, RBAC, org/institution registration, approval workflows — untouched

## 2. Migration Created

**None.** No schema change was required. Registration reuses existing tables/columns:

- `public.users` (link row: `auth_user_id, email, first_name, last_name, display_name, status`)
- `students` (`user_id, institution_id, student_number, email, register_number, university_roll_number, approval_status='pending', enrollment_date, status, is_active`)
- `institution_membership_requests` (`institution_id, organization_id, user_id, requested_role, official_email, full_name, designation, department, status='pending'`)
- `institutions` (`code, organization_id, status, is_active`) — read-only here

## 3. Registration Endpoints

### `POST /api/v1/users/register` (public, unauthenticated)
- Body: `UserRegistrationRequest` (`registration_type, institution_code, email, password, first_name, last_name` + type-specific fields)
- Flow: validate schema → resolve institution by PUBLIC code (must be ACTIVE) → validate identities → create Supabase Auth account (existing mechanism) → create `public.users` link row → students: `students` profile (`approval_status='pending'`); faculty/staff: membership request (pending, NO role) → 201 `UserRegistrationResponse`
- Response never contains password, token, role, or scope fields.

## 4. Supported User Types

- `student` — requires >=1 of `register_number` / `university_roll_number` (blank→None; missing both → 422 `IDENTIFIER_REQUIRED`); creates pending `students` profile. Student identifiers on non-student payloads → 422.
- `faculty` — optional `designation`, `department`; creates pending `institution_membership_requests(requested_role='faculty')`, NO role granted.
- `staff` — same shape as faculty with `requested_role='staff'`, NO role granted.

## 5. Institution Resolution

- Server-side only: `tenancy_repo.get_institution_by_code(db, code.strip().upper())` — client supplies only the public code (case/whitespace-insensitive); never an id, scope, or organization.
- Active-gate: `tenancy_svc._assert_institution_active` requires `status == 'active'` AND `is_active` — pending/rejected/inactive all → 403 `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS`.
- Missing code → 404 `INSTITUTION_NOT_FOUND`. Hierarchy preserved via the institution row's own `organization_id` (used for the membership request); no client-supplied org accepted.

## 6. Role/Scope Behavior

- Client cannot choose roles: `registration_type: Literal["student","faculty","staff"]` + `extra="forbid"` — `"admin"`, `role`, `scope_type`, `scope_id`, `approval_status`, `institution_id`, `organization_id` all rejected with 422 before any service call.

- Server maps `registration_type → requested_role` 1:1 (`ROLE_MAP`); NO `user_roles` write happens at registration for any type. Student role granted later by Phase 6.4 approval; faculty/staff roles granted server-side at membership-request approval (existing 6.13.4 pattern).
- Scope is the resolved `institution.institution_id` (stored on the student profile / membership request); cross-institution access remains denied by existing guards.

## 7. Approval/Pending Behavior

- Every registration starts PENDING: students → `students.approval_status='pending'`; faculty/staff → `institution_membership_requests.status='pending'` with NO role row — no unrestricted protected access before approval (existing pending-account rules apply unchanged).
- No second approval system and no approval endpoint built here; existing Phase 6.4 (students) / 6.13.4 (membership) decision paths grant roles server-side. After approval the user keeps institution scope and cannot reach another institution's data.

## 8. Student Academic Identity Behavior

- Preserves Phase 6 identity model: `email` + `register_number` + `university_roll_number` stored on the `students` row scoped to the resolved institution; `student_number` derived via existing `_derive_student_number` (register_number preferred, else roll number).
- Duplicates rejected institution-scoped via existing `_assert_no_duplicate_identities`: same-institution email → 409 `EMAIL_ALREADY_REGISTERED`; register number → 409 `REGISTER_NUMBER_ALREADY_REGISTERED`; roll number → 409 `ROLL_NUMBER_ALREADY_REGISTERED`. Same identifiers at a different institution are not duplicates.
- Existing login methods untouched (`email+password`, `register_number+password+institution_code`, `university_roll_number+password+institution_code`) — this phase only writes compatible identity rows.

## 9. Authentication Integration

- Reuses existing Supabase/GoTrue integration only: `_create_auth_account` (signup) + `_create_public_user` link row. Password goes ONLY to GoTrue — never stored/hashed/logged/echoed by the app; never in responses or DB rows (asserted by tests).
- Partial failures use the Phase 6.3 compensation pattern: `users`-insert failure → delete fresh auth account; `students`/membership-insert failure → delete fresh `users` row + auth account (best-effort, never masks the primary `AppError` → 500 `REGISTRATION_FAILED`).

## 10. Security/Tenant-Isolation Behavior

- Inactive/pending/rejected institutions cannot accept registrations (403); nonexistent → 404; fail-closed when tenant context unresolvable.
- No arbitrary institution-ID or org override: only the public code is accepted and server-resolved; membership requests inherit `organization_id` from the institution row.
- No self-registration as `admin` (unrepresentable Literal + forbid-extra → 422); no role/scope/status injection; no role granted at registration (response contains no role/scope fields).
- Passwords never exposed (response/row/text assertions); tenant isolation asserted (stored `institution_id` == resolved institution == response `institution_id`).

## 11. Tests Run

- Targeted: `backend/tests/test_user_registration_phase_6_13_5.py` — **39 passed**
- Full backend suite: `backend/tests/` — **1178 passed, 15 skipped, 0 failures**
- Phases 6.13.1–6.13.4 regression files all green within the full run (no modifications to those modules).

## 12. Exact Test Results

```
tests/test_user_registration_phase_6_13_5.py   39 passed
Full backend suite                             1178 passed, 15 skipped, 0 failures
```

Targeted coverage (25 required areas → 39 tests): student/faculty/staff success (3), nonexistent/pending/rejected/inactive institution (4), role assignment x3 + admin-injection + no-role-at-registration (5), institution-scope + cross-institution isolation + code normalization (3), duplicate email/register/roll (3), invalid email/password/missing fields (3), password-not-returned/not-stored (2), partial-failure compensation x3 + auth failure (4), tenant-mismatch guard, login-compat regression marker, 6.13.1–6.13.4 regression marker.

## 13. Remaining Limitations

- **Approval UI/workflow for these registrations** — not built here; pending students/faculty/staff are approved through the existing Phase 6.4 / 6.13.4 decision paths.
- **No new login methods or auth redesign** — existing Supabase/Auth + Phase 6 login methods unchanged.
- **No frontend registration UI, dashboards, attendance, results, chatbot, or RAG changes** — out of scope per brief.
- **No new roles and no org/institution redesign** — `admin + institution scope` convention preserved; no `institution_admin` introduced.
- **No migration** — none needed; a future hardening pass could add DB-level UNIQUE enforcement mirrors, but service-level checks + existing Phase 6.2 keys already cover duplicates.

