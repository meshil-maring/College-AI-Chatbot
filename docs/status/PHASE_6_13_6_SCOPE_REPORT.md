# PHASE 6.13.6 — Multi-Identifier Sign In

## 1. Files Changed

### New Files
- `backend/app/services/sign_in.py` — post-authentication sign-in status guard (thin additive seam; reuses the Phase 6.5 institution gate, defines no second status system)
- `backend/tests/test_sign_in_phase_6_13_6.py` — 84 focused tests covering all 25 required areas (mocked Supabase clients; no live services)

### Modified Existing Files (extended, not redesigned)
- `backend/app/api/auth.py` — `POST /auth/login` extended IN PLACE with the status guard (2 imports + 16 lines). Request schema now uses `extra="forbid"`. `POST /auth/signup` untouched.
- `backend/app/db/supabase.py` — added `get_sign_in_context()` (additive sibling of `get_user_by_auth_id`; the locked projection/return contract is unchanged)

### Verified Unchanged
- `backend/tests/test_organization_institution_phase_6_13_1.py` — inspected and confirmed byte-identical to the committed version (the table name list at line ~893 reads `"students", "documents", "knowledge_chunks", "conversations"`); no correction was needed in the final state.

### Deliberately Untouched
- `backend/app/api/student_auth.py` — `POST /auth/student/login` (Phase 6.5) unchanged; all three student login methods preserved byte-for-byte
- `backend/app/services/student_auth.py` — `authenticate_student`, `_resolve_identity`, `_resolve_academic_id_with_context`, `_assert_institution_active`, `SafeAuthFailure` reused as-is (no rewrite, no duplicate)
- `backend/app/core/security.py` — `get_current_user` / `require_roles` / `scope_tenant` / `assert_tenant_object` unchanged (Phase 6.6 boundary intact)
- `backend/app/services/authorization.py`, `repositories/tenancy.py`, `services/tenancy.py`, `services/user_registration.py` — role/scope/user registration unchanged
- Frontend — no UI work (out of scope)

## 2. Migration Created

**None.** No schema change was required. Phase 6.13.6 reads only existing columns:

- `public.users` (`auth_user_id`, `user_id`, `status`) — Phase Admin-1
- `students` (`user_id`, `institution_id`, `email`, `register_number`, `university_roll_number`, `approval_status`, `is_active`, `status`) — Phases 6.2 / 6.3
- `institutions` (`institution_id`, `code`, `organization_id`, `status`, `is_active`) — Phase 6.13 (`is_active` is trigger-derived from `status`)
- `user_roles` (`scope_type`, `scope_id`, `scope_organization_id`) — Phase 6.13

## 3. Login Endpoints

Two existing endpoints — **no new endpoint was added, and no auth API redesign**:

| Endpoint | Status | Purpose |
|---|---|---|
| `POST /api/v1/auth/login` | **extended in place** | email + password sign-in for every account on the existing email identity model (admin, faculty, staff, students) |
| `POST /api/v1/auth/student/login` | unchanged (Phase 6.5) | multi-identifier student sign-in |

## 4. Supported Login Identifiers

```text
Email + Password                                   (both endpoints)
Register Number + Password + Institution Code      (student endpoint)
University Roll Number + Password + Institution Code (student endpoint)
```

Faculty / staff / admin sign in with the **existing** identity fields only — `public.users.email` + Supabase Auth password. No new login identifier was invented (Phase 6.13.5 registers faculty/staff with that same email identity).

## 5. Authentication Flow

### `POST /api/v1/auth/login` (email)
```text
client {email, password}
  └─ AuthRequest(extra="forbid")            # role/scope/status/institution_id
                                            #   rejected with 422 before any call
  └─ Supabase Auth (GoTrue) sign_in_with_password   # SINGLE credential authority
       ├─ AuthApiError(400) -> 400 INVALID_CREDENTIALS  (locked Phase 5.4 contract)
       └─ session.access_token
  └─ get_sign_in_context(response.user.id)  # tenant-resolution mechanism
  └─ assert_sign_in_allowed(get_admin_client(), account)   # Phase 6.13.6 guard
       └─ SafeAuthFailure -> 400 INVALID_CREDENTIALS, message "Invalid login credentials"
  └─ 200 {"access_token", "message": "Login successful.", "user": {"id", "email"}}
```

### `POST /api/v1/auth/student/login` (identifier)
```text
client {identifier, password, institution_code?}
  └─ _resolve_identity()
       ├─ email            -> global email lookup (no institution context)
       └─ academic id      -> institution_code REQUIRED (else fail-closed)
            └─ _find_institution_by_code ── 404 -> generic failure
            └─ institution-scoped register / roll number lookup
                 ├─ none matched          -> generic failure
                 └─ two different students -> SafeAuthFailure (ambiguous)
  └─ _assert_approved / _assert_student_active / _assert_institution_active
  └─ Supabase Auth sign_in_with_password  # password sent ONLY to GoTrue
  └─ 200 {"access_token", "message", "user"}
```

Both paths normalize every denial to the failure response their respective locked phase defines, so account existence, approval state, and lifecycle state are never disclosed.

## 6. Tenant Resolution

- **Never client-supplied.** `scope_tenant()` / `assert_tenant_object()` (Phase 6.6) plus the Phase 6.13 `user_roles` scope columns remain the only source of tenant identity.
- Email login: `auth.users` → `public.users` (`get_sign_in_context`, keyed on the Supabase Auth user id) → `students.institution_id` → `institutions` (status/`is_active`).
- Academic-identifier login: client supplies only the **public institution code**; the server resolves the institution row (`get_institution_by_code`, case/whitespace-normalized) and then the student **inside that institution** (`get_student_by_register_number` / `get_student_by_university_roll_number`, both `.eq("institution_id", ...)`).
- Post-login scope: `get_user_by_auth_id()` → `resolve_authorization_context()` → `user_roles(scope_type, scope_id, scope_organization_id)`.
- Legacy pre-6.13 rows (`scope_type IS NULL`) stay at **institution** scope for tenant-bound accounts — they are never widened to platform.

## 7. Role / Scope Behavior

```text
Authentication (who)  ->  Authorization (what)
JWT sub -> users.user_id -> user_roles + scope  ->  RBAC (roles)  ->  scope checks
```

- Role and scope are read **only** from trusted server-side records (`user_roles`, `students`). The client cannot supply or override `role`, `roles`, `is_admin`, `user_id`, `auth_user_id`, `status`, `approval_status`, `institution_id`, `organization_id`, `scope_type`, `scope_id`, or `scope_organization_id` — all are rejected `422` by `extra="forbid"` (login) and by the Literal/forbidden schemas (student login).
- `POST /auth/login` returns exactly `{access_token, message, user:{id, email}}` — no role or scope fields are echoed, so an injected role has no channel through which to land.
- RBAC behaviour is unchanged: a tenant-bound admin/staff is pinned to their own institution (`TENANT_MISMATCH` on a foreign `institution_id` query parameter), platform admins keep their existing global passthrough, faculty keep the existing `admin/staff/faculty` ingestion boundary and remain denied the admin-only boundary.
- Pending faculty/staff hold **no** `user_roles` row (Phase 6.13.5) → protected access is denied by RBAC without any new logic.

## 8. Pending / Rejected / Inactive Behavior

```text
users.status != 'active'                -> sign-in denied (include email login)
students approval_status != 'approved'  -> sign-in denied (email + identifier login)
students.is_active == False             -> sign-in denied
institution status/is_active not ACTIVE -> sign-in denied (INVALID_CREDENTIALS)
                                          + protected access denied (403 on /me/*)
```

- One status seam only: the sign-in guard reuses `student_auth._assert_institution_active` (the Phase 6.5 gate) rather than duplicating institution status logic. Non-active statuses all carry `is_active = False` (Phase 6.13 trigger derives it from `status`), so `pending` / `rejected` / `inactive` / `suspended` are all covered by that single check.
- `None`/unknown values fail closed (only the literal `active` passes).
- Denials use `SafeAuthFailure` on the student endpoint (401) and the normalized `400 INVALID_CREDENTIALS` on the email endpoint.

## 9. Security Behavior

- Passwords are never returned, never logged, never stored and never hashed by this application — the password is forwarded to Supabase Auth exactly once (asserted by inspecting every mock call and the captured log records).
- Denials are indistinguishable from a wrong password (same status, same code, same message) → no account/approval/lifecycle enumeration.
- Academic identifiers are scoped by institution, so a register number or roll number that exists in another institution is simply not found (`INVALID_CREDENTIALS`, never 404, never a cross-tenant read).
- No second token system: the existing Supabase Auth session/JWT is returned unchanged and the `auth_id` (`users.auth_user_id` ↔ `auth.users.id`) relationship is untouched.
- Existing frontend response contract preserved (`access_token` / `message` / `user{id,email}`).
## 10. Tests Run

All commands run from `backend/` in the project virtualenv (Python 3.13,
pytest 9.x). No live Supabase project is contacted — every test mocks the
Supabase clients at the module seam.

| # | Command | Scope |
|---|---|---|
| 1 | `python -m pytest tests/test_sign_in_phase_6_13_6.py -q` | Phase 6.13.6 targeted (all 25 required areas) |
| 2 | `python -m pytest tests/test_student_registration_phase_6_3.py tests/test_student_auth_phase_6_5.py tests/test_organization_institution_phase_6_13_1.py tests/test_organization_registration_phase_6_13_2.py tests/test_institution_registration_phase_6_13_3.py tests/test_approval_workflow_phase_6_13_4.py tests/test_user_registration_phase_6_13_5.py -q` | Phase 6.3 + 6.5 + 6.13.1–6.13.5 regression |
| 3 | `python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py -q` | Full backend regression |

### Required-area → test mapping (run 1)

| Requirement | Test(s) |
|---|---|
| 1. student email login | `test_01_student_email_login_succeeds`, `test_12b_active_student_email_login_succeeds` |
| 2. student register-number login | `test_02_student_register_number_login_succeeds`, `test_20b_tenant_resolution_after_academic_identifier_login` |
| 3. student university-roll-number login | `test_03_student_university_roll_number_login_succeeds` |
| 4. register number + wrong institution code | `test_04_register_number_wrong_institution_code_denied`, `test_19b_cross_institution_login_requires_correct_institution_code` |
| 5. roll number + wrong institution code | `test_05_roll_number_wrong_institution_code_denied` |
| 6. nonexistent student | `test_06_nonexistent_student_denied` |
| 7. wrong password | `test_07_wrong_password_denied`, `test_24b_phase_6_email_login_wrong_password_contract_unchanged` |
| 8. pending user | `test_08_pending_user_sign_in_denied`, `test_08b_pending_user_email_login_denied`, `test_25f_phase_6_13_5_student_login_still_requires_registered_identity` |
| 9. rejected user | `test_09_rejected_user_sign_in_denied`, `test_09b_inactive_student_profile_sign_in_denied`, `test_09c_rejected_user_email_login_denied` |
| 10. inactive institution | `test_10_inactive_institution_denied`, `test_10b_inactive_institution_email_login_denied` |
| 11. pending institution | `test_11_pending_institution_denied`, `test_11b_pending_institution_email_login_denied`, `test_25c_phase_6_13_5_registration_gate_semantics_unchanged` |
| 12. approved/active student | `test_12_approved_active_student_succeeds`, `test_12b_active_student_email_login_succeeds`, `test_12c_missing_public_users_row_denied`, `test_12d_non_active_users_status_denied` |
| 13. faculty login | `test_13_faculty_login_succeeds_with_existing_email_identity`, `test_13b_pending_faculty_has_no_role_so_protected_access_denied`, `test_13c_approved_faculty_role_resolved_server_side` |
| 14. staff login | `test_14_staff_login_succeeds_with_existing_email_identity`, `test_14b_pending_staff_has_no_role_so_protected_access_denied`, `test_14c_approved_staff_role_resolved_server_side` |
| 15. admin login compatibility | `test_15_admin_login_remains_compatible`, `test_24h_get_current_user_projections_still_drive_rbac` |
| 16. role cannot be overridden | `test_16_role_cannot_be_overridden_on_email_login`, `test_16b_role_cannot_be_overridden_on_student_login`, `test_16c_other_authorization_fields_cannot_be_overridden`, `test_16d_login_response_never_echoes_role_or_scope`, `test_16e_self_declared_role_is_ignored_by_rbac` |
| 17. institution scope cannot be overridden | `test_17_institution_scope_cannot_be_overridden`, `test_17b_tenant_bound_admin_cannot_request_foreign_institution`, `test_17c_tenant_bound_admin_own_institution_is_scoped_not_substituted` |
| 18. organization scope cannot be overridden | `test_18_organization_scope_cannot_be_overridden`, `test_18b_organization_scope_comes_from_user_roles_only`, `test_25b_phase_6_13_3_scope_accessors_unchanged` |
| 19. cross-institution access denied | `test_19_cross_institution_access_denied`, `test_19b_cross_institution_login_requires_correct_institution_code`, `test_19c_cross_institution_student_lookup_uses_scoped_query`, `test_25a_phase_6_13_1_hierarchy_guard_unchanged` |
| 20. tenant resolution after login | `test_20a_tenant_resolution_after_email_login`, `test_20b_tenant_resolution_after_academic_identifier_login`, `test_20c_authorization_context_resolves_scope_from_user_roles`, `test_20d_legacy_unscoped_tenant_row_is_not_widened_to_platform` |
| 21. invalid login input | `test_21a_student_login_invalid_input_rejected`, `test_21b_academic_identifier_requires_institution_code`, `test_21c_blank_institution_code_rejected`, `test_21d_unknown_institution_code_denied_generically`, `test_21e_email_login_invalid_input_rejected`, `test_21f_malformed_json_body_rejected` |
| 22. password never returned | `test_22a_password_never_returned_on_student_login_success`, `test_22b_password_never_returned_on_email_login_success`, `test_22c_password_never_returned_on_failure`, `test_22d_no_password_field_in_any_login_payload` |
| 23. password never logged/stored | `test_23a_password_never_logged`, `test_23b_password_never_written_to_database`, `test_23c_password_never_persisted_by_the_service_layer`, `test_23d_password_forwarded_only_to_supabase_auth`, `test_23e_login_schemas_carry_no_password_storage_field` |
| 24. existing Phase 6 login regression | `test_24a`–`test_24h` (response shape, failure contract, `SafeAuthFailure` shape, `get_current_user` 401/404 behaviour, RBAC projections) |
| 25. Phase 6.13.1–6.13.5 regression | `test_25a`–`test_25f` (hierarchy guard, scope accessors, registration gate semantics, role map, single status seam, pending registration cannot log in) |

Both success and fail-closed paths are exercised; every denial assertion checks
the status code AND the error code (never a bare truthiness check).

## 11. Exact Results

```text
(1) cd backend; python -m pytest tests/test_sign_in_phase_6_13_6.py -q
    -> 84 passed, 2 warnings in 4.23s

(2) cd backend; python -m pytest tests/test_student_registration_phase_6_3.py
        tests/test_student_auth_phase_6_5.py
        tests/test_organization_institution_phase_6_13_1.py
        tests/test_organization_registration_phase_6_13_2.py
        tests/test_institution_registration_phase_6_13_3.py
        tests/test_approval_workflow_phase_6_13_4.py
        tests/test_user_registration_phase_6_13_5.py -q
    -> 259 passed, 4 skipped, 4 warnings in 8.96s

(3) cd backend; python -m pytest tests -q
    -> 1262 passed, 15 skipped, 7 warnings in 19.76s
```

- **Failures: 0.**
- The only non-passing outcomes are the project's pre-existing, intentionally
  skipped opt-in physical-validation / fixture-gated tests, unchanged from the
  Phase 6.13.5 baseline.
- Warnings are pre-existing third-party deprecations (`starlette.testclient`
  httpx alias, `supabase` `timeout`/`verify` params, Pydantic
  `TestResultCreate` / `TestResultUpdate` collection notices) and are unrelated
  to Phase 6.13.6.
## 12. Remaining Limitations

1. **No frontend sign-in UI** — explicitly out of scope. The login response
   contract is unchanged (`access_token` / `message` / `user{id,email}`), so the
   existing frontend keeps working without modification.
2. **Faculty/staff authenticate by email only.** Phase 6.13.5 registers them
   with the existing `users.email` + Supabase Auth identity; the schema has no
   staff/faculty identifier column and none was invented (per the instruction
   to reuse existing identity fields and not to invent unnecessary login
   identifiers). Academic-identifier login therefore remains students-only.
3. **Membership/join-code redemption is registration-only.** Sign-in does not
   accept a `join_code` or membership-request token; that belongs to the
   Phase 6.13.5 registration flow.
4. **Tenant isolation is application-level plus database triggers — not RLS.**
   Cross-institution reads/writes are blocked by the existing tenant guards
   (`scope_tenant`, `assert_tenant_object`, `TENANT_MISMATCH`) and the Phase
   6.13 `phase613_assert_child_organization` triggers, consistent with the
   existing service-role architecture.
5. **`students.email` and `users.email` are distinct columns.** A student whose
   institutional `students.email` differs from their Supabase Auth
   `users.email` signs in with the Auth email; academic-identifier login uses
   `students.email` case-insensitively. Reconciling the two is out of scope.
6. **Institution lifecycle is not re-checked on every request for non-student
   accounts.** The institution gate runs at sign-in and at the student
   `/me/*` eligibility check (existing Phase 6.9 behaviour). A long-lived
   faculty JWT issued before the institution was deactivated stays valid until
   it expires — token revocation is not in scope for this phase.
7. **All status denials are normalized** to `INVALID_CREDENTIALS` (401 on the
   student endpoint, 400 on the email endpoint) without a distinct code. This
   is a deliberate anti-enumeration choice; operators cannot distinguish
   "pending" from "wrong password" from the API response alone and must consult
   the approval queue / audit log.
8. **No rate limiting or account lockout** was added to the login endpoints;
   this matches the pre-existing behaviour (deferred, not regressed).
9. **No new migration, no new endpoint, no new roles, no new auth provider.**
   Supabase Auth remains the single credential authority and `auth_user_id`
   remains the only link between `auth.users` and `public.users`.