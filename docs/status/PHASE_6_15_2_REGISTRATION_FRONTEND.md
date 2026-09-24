# Phase 6.15.2 — Student Registration Frontend & Institution Resolution

> Implementation phase. Backend contracts were re-verified against the actual
> repository source **before** any change (per Phase 6.15.2 §1), and one
> contract statement from the Phase 6.15.1 audit was found to be superseded by
> newer code — documented explicitly in §2. Date: 2026-09-20 (branch `main`).

---

## 1. Objective

Provide a complete, production-quality student registration experience
(student self-registration with institution-code resolution, pending-approval
success state, and Login ↔ Registration navigation) **without changing the
existing authentication architecture**, RBAC, approval workflow, student
schema, password handling, or token behavior.

---

## 2. Existing Registration Contract (verified, repository as source of truth)

Two public registration endpoints were verified:

### 2.1 `POST /api/v1/registration` (Phase 6.3 — `backend/app/api/registration.py`)

| Item | Verified value |
| ---- | -------------- |
| Request schema | `StudentRegistrationRequest` (`extra="forbid"`): `institution_id: UUID`, `email: EmailStr`, `password` (min 6), `first_name` (non-blank), `last_name` (non-blank), `register_number?`, `university_roll_number?`, `enrollment_date?` |
| Identifier rule | At least one of `register_number` / `university_roll_number` required → `422 IDENTIFIER_REQUIRED` |
| Response schema | `RegistrationResponse`: `message`, `student_id`, `institution_id`, `email`, `approval_status` (always `'pending'`) |
| Approval behavior | `approval_status='pending'` always; approval is exclusively the Phase 6.4 admin workflow |
| Requires | A **client-supplied `institution_id` UUID** |

### 2.2 `POST /api/v1/users/register` (Phase 6.13.5 — `backend/app/api/users.py`) — **supersedes the audit**

The Phase 6.15.1 audit did not list this endpoint. The repository contains a
**newer unified public registration endpoint** for students, faculty, and
staff, explicitly documented in-code as *"This endpoint replaces the need for
separate student/faculty/staff registration endpoints."*

| Item | Verified value |
| ---- | -------------- |
| Request schema | `UserRegistrationRequest` (`extra="forbid"`): `registration_type: Literal['student','faculty','staff']`, `institution_code` (2–64 chars, **normalized to upper-case, resolved SERVER-SIDE**), `email: EmailStr`, `password` (min 6), `first_name` (non-blank), `last_name` (non-blank), `register_number?`, `university_roll_number?` |
| Identifier rule | Same `IDENTIFIER_REQUIRED` rule for students; academic identifiers are rejected for faculty/staff |
| Response schema | `UserRegistrationResponse` (201): `message`, `user_id`, `institution_id`, `institution_code`, `registration_type`, `approval_status` (`'pending'`), `student_id`, `request_id` |
| Approval behavior | Always `'pending'`; student role is granted only by the existing Phase 6.4 approval workflow |
| Security design | The schema doc states: *"Public registration payloads never accept internal database ids; they use the public code (`institution_code`), which the server resolves to an id."* |

### 2.3 Error contract (`backend/app/core/errors.py` + `app/main.py`)

AppError envelope `{"error": {"code", "message"}}`; FastAPI validation failures
normalized by the project handler to `422 {"error":{"code":"VALIDATION_ERROR",...}}`.
Verified codes relevant to registration:

| Code | HTTP | Meaning |
| ---- | ---- | ------- |
| `EMAIL_ALREADY_REGISTERED` | 409 | account with this email exists (incl. GoTrue email-exists translation) |
| `STUDENT_ALREADY_REGISTERED` | 409 | email already linked to a students profile |
| `REGISTER_NUMBER_ALREADY_REGISTERED` | 409 | duplicate register number (institution-scoped) |
| `ROLL_NUMBER_ALREADY_REGISTERED` | 409 | duplicate university roll number (institution-scoped) |
| `INSTITUTION_NOT_FOUND` | 404 | unknown institution |
| `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS` | 403 | institution exists but is not ACTIVE |
| `IDENTIFIER_REQUIRED` | 422 | neither academic identifier supplied |
| `VALIDATION_ERROR` | 422 | request validation failure |

### 2.4 Student login contract (unchanged, for context)

`POST /api/v1/auth/login` (email+password), `POST /api/v1/auth/student/login`
(email / register number / university roll number; academic identifiers require
`institution_code`). **Not modified in this phase.**

---

## 3. Institution Resolution Strategy

Search confirmed **no public institution-code → institution-id lookup endpoint
existed**. Two options existed:

1. Frontend resolves `code → institution_id` via a new lookup endpoint, then
   submits `POST /api/v1/registration` with the resolved UUID (the brief's
   assumed shape), or
2. Submit through the newer `POST /api/v1/users/register`, which resolves the
   code **server-side** — no UUID ever handled by the browser.

**Decision: option 2 for submission**, because it is the repository's current
contract (§2.2), it exceeds the brief's security minimum (§6 "do not trust a
user-supplied institution UUID" — the browser never holds one at all), and its
schema explicitly forbids internal ids in public payloads.

For the required resolution **UX** (confirming the code shows the institution
name *before* submitting), a minimal read-only lookup endpoint was added (§4).
The frontend may display the returned id, but registration itself re-resolves
and re-validates the code server-side, so the backend remains authoritative.

---

## 4. API Changes

One new endpoint; **no existing endpoint or schema was modified**.

### `GET /api/v1/institutions/lookup?code=<code>`

| Item | Value |
| ---- | ---- |
| Method | GET |
| Path | `/api/v1/institutions/lookup` |
| Authentication | **None** — deliberately public for unauthenticated registration discovery (mirrors the public registration endpoints; no existing authenticated endpoint was weakened) |
| Request | Query param `code` (required, 2–64 chars; case-insensitive — normalized upper-case server-side) |
| Response (200) | `InstitutionLookupResponse`: `{"institution_id": "<uuid>", "code": "IMPHAL", "name": "Example College"}` — **only** these three safe public fields |
| Invalid institution | 404 `INSTITUTION_NOT_FOUND` (unknown code) |
| Not joinable | 403 `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS` (institution exists but not ACTIVE) |
| Validation behavior | 422 `VALIDATION_ERROR` for missing/blank/short code (FastAPI `Query` constraints + service guard) |
| Never exposed | contact email, address/city/state/country, `status`, `is_active`, `organization_id`, join codes, timestamps, credentials, student/admin data |

Files: `backend/app/api/institutions.py`, `backend/app/services/tenancy.py`
(new `lookup_institution_by_code` reusing `tenancy_repo.get_institution_by_code`
and `_assert_institution_active`), `backend/app/schemas/tenancy.py` (new
`InstitutionLookupResponse`).

---

## 5. Frontend Components Added/Modified

| File | Change |
| ---- | ------ |
| `frontend/src/features/auth/RegistrationForm.tsx` | **NEW** — the registration page (form + resolution UX + pending-approval success state) |
| `frontend/src/features/auth/LoginForm.tsx` | Added `Register as Student` navigation; renders `RegistrationForm` and receives it back via `Back to Login` (same conditional-rendering pattern as the existing `ForgotPasswordForm`) |
| `frontend/src/services/registration.ts` | **NEW** — API client: `lookupInstitution()`, `registerStudent()`, typed `RegistrationError` + `registrationErrorMessage()` |
| `frontend/src/types/registration.ts` | **NEW** — `InstitutionLookupResponse`, `RegistrationRequest`, `RegistrationResponse` |
| `frontend/src/features/auth/LoginForm.test.tsx` | Added Login ↔ Registration navigation tests |
| `frontend/src/features/auth/RegistrationForm.test.tsx` | **NEW** — full form test suite |
| `frontend/src/services/registration.test.ts` | **NEW** — HTTP-boundary error-classification tests |

No new UI framework, router, HTTP library, or second API client was introduced;
`RegistrationForm` reuses the LoginForm/ForgotPasswordForm visual language
(Tailwind slate/emerald cards, wrapped labels, `role="alert"`/`role="status"`
regions) and the `services/auth.ts` client conventions.

---

## 6. Registration Flow

```
LoginForm  ──"Register as Student"──▶  RegistrationForm
   │                                        │ student types institution code
   │                                        ▼ (blur / before submit)
   │                              GET /api/v1/institutions/lookup?code=…
   │                                        │
   │                        ┌───────────────┼──────────────────┐
   │                    found           not found         not accepting
   │              "Imphal College"   controlled error    controlled error
   │                                        │
   │                              (submit only with resolved institution)
   │                                        ▼
   │                            POST /api/v1/users/register
   │                            registration_type='student'
   │                                        │
   │                              201 approval_status='pending'
   │                                        ▼
   │                          Pending-approval success panel
   │                        (NO token, NO auth-state change)
   └──"Back to Login"───────────────────────┘
```

Key invariants implemented:

* **Invalid registration is impossible client-side**: submit requires
  valid student fields + a resolved institution + valid + matching passwords;
  the submit path re-resolves the code on demand if it changed, so a stale
  resolution can never be submitted.
* **No client-supplied institution UUID exists anywhere** in the request.
* **Registration ≠ authentication**: the 201 response carries no token; the
  `AuthProvider` state is never touched. The student is NOT logged in; they
  see the pending-approval confirmation and return to Login.

---

## 7. Validation Rules (client-side, mirroring the backend exactly)

| Field | Rule | Backend mirror |
| ----- | ---- | -------------- |
| Full Name | required, ≥ 2 chars; split into `first_name` + `last_name` (multi-token → first token + remainder; single token → reused as last name to satisfy the non-blank rule) | `first_name`/`last_name` non-blank validators |
| Email | required, valid format | `EmailStr` |
| Register Number | optional | optional; normalized (blank→null) server-side |
| University Roll Number | optional | optional; normalized server-side |
| (both identifiers) | at least one required | `422 IDENTIFIER_REQUIRED` |
| Institution Code | required, 2–64 chars, must resolve to an ACTIVE institution | `institution_code` Field constraints + server resolution |
| Password | required, ≥ 6 chars | password validator (`min_length=6`) |
| Confirm Password | must equal password | (frontend-only, prevents typo'd passwords) |

No invented stricter rules were added beyond the existing frontend pattern
(`minLength={6}` + match confirmation, consistent with `ForgotPasswordForm`).

---

## 8. Error Handling

Errors are classified from backend error **codes** (`RegistrationErrorKind`)
in `services/registration.ts`; the UI renders fixed, user-safe messages.
Never displayed: stack traces, SQL errors, SQLSTATE, constraint names,
internal ids (beyond the institution name), backend internals, secrets.

| Situation | Backend code | UI message |
| --------- | ------------ | ---------- |
| Unknown institution | `INSTITUTION_NOT_FOUND` (404) | "Institution code was not found. Please check the code and try again." |
| Institution inactive | `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS` (403) | "This institution is not currently accepting registrations." |
| Duplicate email | `EMAIL_ALREADY_REGISTERED` / `STUDENT_ALREADY_REGISTERED` (409) | "An account with this email already exists." |
| Duplicate register number | `REGISTER_NUMBER_ALREADY_REGISTERED` (409) | "This register number is already registered." |
| Duplicate roll number | `ROLL_NUMBER_ALREADY_REGISTERED` (409) | "This university roll number is already registered." |
| Validation failure | `VALIDATION_ERROR` (422) | "Please review the highlighted fields and try again." |
| Server error | 5xx | "The server reported an error. Please try again later." |
| Network failure | no HTTP response | "Could not reach the backend. Please make sure the server is running, then try again." |
| Timeout | aborted request | "The request timed out. Please try again." |
| Unexpected response | other | "Something went wrong. Please try again." |

Lookup failures inside the form show the same controlled messages inline under
the Institution Code field (`aria-live="polite"`), never raw API output.
Timeouts: 10s lookup / 20s registration via `AbortController`.

---

## 9. Approval-Pending Flow

Verified backend behavior: self-registration **always** creates
`approval_status='pending'` and returns **no token**. Implemented flow:

```
Registration successful (201, approval_status='pending')
   → "Registration Successful" panel
       "Your student account has been created."
       "Your account is currently waiting for approval from your college
        administrator or staff."
       "You will be able to log in after your account has been approved."
   → [ Back to Login ]
   → Admin/Staff approves (existing Phase 6.4 / 6.13.4 workflow)
   → Student logs in through the EXISTING login endpoints
```

The AuthProvider status remains `'unauthenticated'` throughout; the frontend
deliberately distinguishes *registration successful* from *authentication
successful*, and never redirects to the dashboard after registration.

---

## 10. API Client Changes

`frontend/src/services/registration.ts` (new; mirrors `services/auth.ts`
conventions — typed error kinds, AppError-envelope parsing, fetch-level
network detection, no secrets in messages):

* `lookupInstitution(code, timeoutMs=10_000)` → `GET /api/v1/institutions/lookup?code=…`
* `registerStudent(request, timeoutMs=20_000)` → `POST /api/v1/users/register`
* `RegistrationError` with `kind` / `status` / `code`; `registrationErrorMessage()`

Types (`frontend/src/types/registration.ts`): `InstitutionLookupResponse`,
`RegistrationType`, `RegistrationRequest`, `RegistrationResponse` — all
snake_case mirrors of the verified backend schemas; **no `any`**.
`services/api.ts`, `services/auth.ts`, `services/adminApi.ts`, and
`services/devAuth.ts` are untouched (no second API client).

---

## 11. Tests Added

### Frontend

* `src/features/auth/RegistrationForm.test.tsx` (21 tests)
  * Rendering: all fields present, submit + navigation controls present,
    back-to-login navigation from the form.
  * Validation: empty required fields, invalid email, missing identifier,
    short password, password mismatch — submission blocked.
  * Lookup: success (name shown + endpoint called with the typed code),
    invalid code, loading state ("Finding institution…"), network failure,
    and refusal to submit with an unresolved institution.
  * Registration: exact request schema asserted (all 8 fields), roll-number
    fallback, multi-token name split, duplicate email / register number /
    roll number, backend validation error, network failure.
  * Loading states: submit disabled + inputs disabled + duplicate-submission
    prevention while `registerStudent` is in flight.
  * Approval: pending-approval copy shown, form unmounted (not logged in),
    back-to-login from the success state.
* `src/features/auth/LoginForm.test.tsx` (+2 tests): Login → Registration and
  Registration → Login navigation.
* `src/services/registration.test.ts` (15 tests): request URL/method/body
  verification, URL encoding, and full error-code → kind → message mapping
  (404/403/409×4/422/500/network/timeout), password never leaked in errors.

### Backend

* `backend/tests/test_institution_lookup_phase_6_15_2.py` (9 tests): valid
  code, case-insensitive normalization, unknown code (404), short code (422),
  missing code (422), blank code (422, DB never touched), inactive
  institution (403), **safe response projection** (exact key set; forbidden
  fields asserted absent), no-authentication requirement.

---

## 12. Test Results

### Frontend (`npm test`, `npm run build`)

| Suite | Result |
| ----- | ------ |
| Test files | 14 passed, 0 failed |
| Tests | **108 passed**, 0 failed, 0 skipped |
| `tsc -b && vite build` (typecheck + build) | ✅ success |

### Backend (`pytest`, Python 3.13)

| Scope | Result |
| ----- | ------ |
| New lookup tests | 9 passed |
| Relevant regression (registration ×3, institution ×2, student auth, RBAC, tenant isolation, role-scope) | **326 passed**, 4 skipped |
| Full backend suite | **1608 passed**, 15 skipped, **0 failed** |
| Skipped (pre-existing, unrelated) | live-database validations requiring explicit manual opt-in (not new to this phase) |

Failures introduced by Phase 6.15.2: **none** (one initial frontend test had a
wrong assertion about the shared "Email" label; fixed before final run).

---

## 13. Security Considerations

* **No client-supplied institution UUID**: the browser sends only the public
  code; the backend resolves and re-validates it server-side on every
  registration (stronger than the brief's "frontend may hold the resolved UUID").
* **Safe lookup projection**: the new endpoint returns exactly
  `institution_id` / `code` / `name` — enforced by the response model and
  asserted by tests; no contact/location/organization/status/join-code data.
* **Public by design, read-only**: the lookup requires no authentication
  because an unauthenticated student must discover their institution before
  they can authenticate — the same trust level as the existing public
  registration endpoints. No existing authenticated endpoint was weakened.
* **Pending-approval cannot be bypassed**: registration never grants a role
  and never returns a token; the frontend never treats a 201 as a session.
* **Password handling**: sent only in the POST body to the backend (which
  forwards it exclusively to Supabase Auth GoTrue); never stored, logged,
  rendered, or leaked into error messages (test-asserted).
* **Error hygiene**: all failures render fixed user-safe strings resolved from
  backend codes; no SQL/constraint/stack details can reach the UI.
* **Duplicate-submission prevention**: controls disabled during in-flight
  operations; identity duplicates additionally enforced server-side
  (institution-scoped unique constraints).

---

## 14. Files Changed

**Backend**
* `backend/app/api/institutions.py` — added `GET /institutions/lookup`
* `backend/app/services/tenancy.py` — added `lookup_institution_by_code`
* `backend/app/schemas/tenancy.py` — added `InstitutionLookupResponse`
* `backend/tests/test_institution_lookup_phase_6_15_2.py` — **NEW** (9 tests)

**Frontend**
* `frontend/src/features/auth/RegistrationForm.tsx` — **NEW**
* `frontend/src/features/auth/RegistrationForm.test.tsx` — **NEW** (21 tests)
* `frontend/src/services/registration.ts` — **NEW**
* `frontend/src/services/registration.test.ts` — **NEW** (15 tests)
* `frontend/src/types/registration.ts` — **NEW**
* `frontend/src/features/auth/LoginForm.tsx` — registration navigation
* `frontend/src/features/auth/LoginForm.test.tsx` — +2 navigation tests

**Documentation**
* `PHASE_6_15_2_REGISTRATION_FRONTEND.md` — this document

Not modified (per §18 constraint): student schema/model, RBAC, approval
workflow, password hashing, auth tokens, login endpoints, student login,
`services/api.ts`, `services/auth.ts`, `AuthProvider`, or any existing test.

---

## 15. Known Limitations

1. **Full Name split heuristic**: the backend requires separate
   `first_name` / `last_name`; the single-field split ("first token →
   first_name, remainder → last_name"; single token reused) is a pragmatic
   mapping. A two-field form would require a backend contract change (out of
   scope per §18).
2. **Lookup is code-based only**: institutions are discovered solely by their
   public code (no fuzzy search / listing — deliberately, to keep the public
   surface minimal).
3. **`enrollment_date` not exposed**: `POST /api/v1/registration` accepts an
   optional `enrollment_date`; the unified endpoint defaults it to today
   server-side, so the form omits it (no invented fields).
4. **Client-side validation is a UX aid only** — the backend remains
   authoritative (e.g., identity uniqueness is only decidable server-side).
5. **Registration responsiveness** was kept consistent with the existing
   login card (`max-w-md`, fluid width, `px-4`); the shared design system was
   not visually re-audited on physical devices (code-level responsive classes
   verified only).

---

## 16. Final Verification

| Definition-of-Done item | Status |
| ----------------------- | ------ |
| Registration backend contract verified | ✅ §2 (incl. audit discrepancy documented) |
| Institution resolution strategy implemented | ✅ §3 |
| Institution lookup works | ✅ §4 + frontend tests |
| Registration page implemented | ✅ `RegistrationForm.tsx` |
| Registration form uses the real backend schema | ✅ exact-field test |
| Client-side validation implemented | ✅ §7 + tests |
| Institution validation implemented | ✅ resolution gate + submit re-check |
| Registration API integrated | ✅ §6, §10 |
| Duplicate registration errors handled | ✅ §8 + tests |
| Pending approval state implemented | ✅ §9 + tests |
| Login ↔ Registration navigation implemented | ✅ + tests |
| Loading states implemented | ✅ lookup + submission + tests |
| Error handling implemented | ✅ §8 + tests |
| Accessibility verified | ✅ wrapped labels, `role="alert"`/`"status"`, `aria-live`, `aria-describedby`, disabled states, `type="password"` inputs |
| Responsive UI verified | ✅ same responsive card pattern as login (§15.5) |
| TypeScript types updated | ✅ §10, no `any` |
| Frontend tests added | ✅ 38 new tests |
| Backend tests added (lookup endpoint created) | ✅ 9 tests |
| Existing relevant tests pass | ✅ 326 targeted / 1608 full, 0 failures |
| Documentation created | ✅ this file |
| Git changes reviewed | ✅ only the files in §14 |
| No unrelated changes introduced | ✅ confirmed via `git status` |

**Phase 6.15.2 outcome: COMPLETE.** Stopping here per phase instructions —
Phase 6.15.3 has NOT been started.
