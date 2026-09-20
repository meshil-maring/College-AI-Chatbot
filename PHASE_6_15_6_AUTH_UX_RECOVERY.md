# PHASE 6.15.6 — AUTHENTICATION UX HARDENING & ACCOUNT RECOVERY

**Status:** COMPLETE
**Date:** 2026-09-20
**Scope:** Authentication UX consistency, forgot-password / reset / change-password
verification, password visibility & state clearing, validation feedback, error
vocabulary, loading states, accessibility, mobile UX, security regression.
**Architecture:** unchanged. One minimal, security-motivated backend fix
(account enumeration in the dev/test recovery endpoint) — see §2 and §12.

---

## 1. Objective

Harden the user-facing authentication experience on top of the stable
foundation delivered by Phases 6.15.1–6.15.5:

```text
Registration → Institution Resolution → Pending Approval → Student Login
→ /auth/me → server-authoritative role → correct shell → session lifecycle
```

Phase 6.15.6 changed only what a user sees and how failures are communicated.
It did **not** change RBAC, tenant resolution, student identity, JWT handling,
role resolution, the session-expiry contract, or the registration contract.
Nothing was committed.

---

## 2. Existing Recovery Architecture (audited — source of truth)

**The application has NO email/token-based password recovery mechanism.**
There is no reset-link route, no reset-token table, no recovery page, and no
`reset_password_for_email` call anywhere in the repository. Reporting anything
else would be inventing an architecture.

The only implemented recovery path is the **DEV/TEST-only** endpoint pair, and
it is gated server-side:

| Endpoint | Gate | Contract |
|---|---|---|
| `POST /api/v1/dev/auth/forgot-password` | `DEV_TEST_MODE=true`, else `404 NOT_FOUND` | `{ email, new_password, confirm_password }` → `200 { message }` (direct Supabase Auth admin password update; no OTP/email) |
| `POST /api/v1/dev/auth/change-password` | same | `{ email, current_password, new_password, confirm_password }` → `200 { message }` (current password proven via normal Supabase sign-in, then admin update) |
| `POST /api/v1/dev/auth/admin/reset-student-password` | same **+ `require_roles("admin")`** | `{ email, new_password, confirm_password }` |
| `GET /api/v1/dev/auth/status` | none | `{ dev_test_mode: boolean }` (fails closed in the client) |

Implementation: `backend/app/api/dev_auth.py` (unchanged apart from the
anti-enumeration normalization in §3). Password rule mirrored from
`app/api/auth.py`: minimum length **6**, no maximum, no complexity classes.

Frontend surfacing (unchanged gating):
`LoginForm` renders the *"Forgot password? (Dev/Test only)"* link only when
`fetchDevAuthStatus()` reports `dev_test_mode === true`; `App.tsx` renders the
change-password panel under the same condition.

**Minimal fix applied (the only backend change):** the dev recovery endpoint
previously answered `404 USER_NOT_FOUND` — *"No account found for that email."*
— for an unknown address, which is a textbook account-enumeration oracle, and
the frontend rendered it verbatim. It now returns the SAME generic `200`
response for a known and an unknown email (`_GENERIC_RECOVERY_MESSAGE`),
matching the anti-enumeration normalization already used by `/auth/login` and
`/auth/student/login`. No production endpoint changed; no test was weakened —
the test asserting the enumerating behavior was replaced by one asserting the
parity contract (§13).

---

## 3. Forgot Password Flow (final state)

```text
Login screen
   ↓ "Forgot password? (Dev/Test only)"   (visible only when the backend flag is on)
Reset Password screen  (amber "Development / Testing Only" banner on the login card layout)
   ↓ Email + New password + Confirm new password
   ↓ client-side validation (field-level messages)
POST /api/v1/dev/auth/forgot-password
   ↓ 200 { message }  — generic, identical for a known and an unknown email
Success state: "Password Reset Submitted"
   ↓ generic anti-enumeration sentence + "Back to Login"
Login screen  (NEVER auto-authenticated; no token exists)
```

* **Request schema:** `{ email: EmailStr, new_password: str(min 6), confirm_password: str }`.
* **Success response:** `200 { "message": "If an account exists for this email, the password has been reset. You can now sign in with your new password. (DEV/TEST ONLY)" }` — byte-identical for both cases.
* **Error behavior:** `404 NOT_FOUND` when the dev flag is off; `422` for request validation; `400 AUTH_ERROR` if Supabase itself fails (operational, not account-existence).
* **Enumeration protection:** backend response parity (above) **and** client copy that never confirms or denies existence.
* **Token/recovery mechanism:** none — a direct admin password update. No token is created, stored, or parsed.
* **Expiration:** not applicable (there is no token).
* **Frontend state handling:** `busy` (single in-flight request), per-field errors, one form-level error for backend failures, and a `submitted` success state. The two plaintext password fields are cleared when the request settles.
* **Identifier support:** email only. Register number / university roll number / institution code are deliberately NOT accepted (the backend recovery contract has no academic-identifier lookup), and a test asserts those fields do not exist on this screen.

---

## 4. Password Reset Flow (reset completion)

Because the recovery endpoint performs the reset **in one request**, the
"reset page" and the "forgot-password page" are the same screen — there is no
second step to verify. Nothing was fabricated to imitate a link-based flow.

Verified end-to-end in tests (`ForgotPasswordForm.test.tsx`, 17 tests):

| Case | Result |
|---|---|
| Token handling | N/A — the architecture has no reset token (documented, not invented) |
| Expired token | N/A — no token exists |
| Invalid token | N/A — no token exists |
| Password validation | Empty → *"Please enter a new password."*; `< 6` → *"Password must be at least 6 characters."* (mirrors the backend) |
| Password mismatch | *"Passwords do not match."* on the confirm field |
| Successful reset | Generic success state, password fields gone, **no token**, **nothing in localStorage/sessionStorage** |
| Safe errors | Server/network/dev-disabled messages only; an unexpected not-found never renders account-existence wording |

The success state satisfies §5 of the phase brief with accurate wording:
`"If an account exists for this email, the password has been reset. You can now
sign in with your new password."` — a "password-reset instructions have been
sent by email" sentence would be false here, since no email is sent (clearly
stated on the same screen, which stays marked "Development / Testing Only").
The user is never authenticated by this flow and no access token is created.

---

## 5. Change Password Flow

```text
Authenticated → "Change Password (Dev/Test only)" panel → form
  Current password / New password / Confirm new password → [Change password]
     ↓ POST /api/v1/dev/auth/change-password (email from /auth/me, never typed)
     ↓ 200 → "Password changed successfully. Your session stays active."
```

Verified against `backend/app/api/dev_auth.py` before touching the fields —
the request schema (`email`, `current_password`, `new_password`,
`confirm_password`) is unchanged.

**Session behaviour after a password change (§17) — taken from the contract,
not assumed:** the handler verifies the current password through the ordinary
Supabase sign-in flow and then calls `auth.admin.update_user_by_id`. No
`sign_out`, no `revoke`, and no session invalidation exists in the repository
(the JWT is stateless and `logout` is client-side only). Therefore:

```text
Change password → current session REMAINS valid
```

The form consequently does **not** sign the user out; a test asserts `logout`
is never called. This is a documented property of the existing JWT
architecture, which Phase 6.15.6 did not modify.

---

## 6. Password Validation (backend = source of truth)

| Rule | Backend source | Frontend mirror |
|---|---|---|
| Minimum length 6 | `app/api/auth.py` `password_min_length`; `app/api/dev_auth.py` `_validate_password`; registration schema | `minLength={6}` + explicit *"Password must be at least 6 characters."* |
| Maximum length | none defined | none added |
| Complexity classes | none defined | none added |
| Confirmation match | `_confirm_matches` validators → `422` | *"Passwords do not match."* |
| Current password required | `DevChangePasswordRequest.current_password` | *"Please enter your current password."* |

No stricter rule was invented. Client-side validation is UX only and always
mirrors the backend; the backend stays authoritative (a `422` still maps to a
user-safe message).

---

## 7. Password Visibility

New shared component: `frontend/src/features/auth/PasswordField.tsx`, used by
all four password surfaces — Login, Registration, Reset Password and Change
Password (7 password inputs in total).

* Renders an explicit `<label htmlFor>` + `<input id>` pair (no control is
  nested inside a `<label>`), so accessible names stay exactly
  `Password` / `Confirm Password` / `New password` / `Current password`.
* A `type="button"` toggle (visible text `Show` / `Hide`) flips **only its own**
  input between `type="password"` and `type="text"`; the value is preserved and
  never read, copied, or exported.
* The accessible name is field-specific and changes with the state
  (`Show current password` → `Hide current password`), is tied to the input via
  `aria-controls`, and contains the visible text (`Show`/`Hide`), satisfying
  WCAG 2.5.3 *Label in Name*. Keyboard operable (`Tab` + `Enter`/`Space`).
* The toggle is disabled together with its input while an operation is running.
* `spellCheck={false}` so a revealed value is not spell-checked.
* Layout is a flex row (`min-w-0 flex-1` input + `shrink-0` button) — no
  absolute positioning, so nothing overlaps or clips at small widths.

---

## 8. Error Handling

One user-facing vocabulary, owned by the service layer:

| Situation | Message |
|---|---|
| Rejected credentials | *Invalid login credentials. Please check your details and try again.* |
| Expired / invalid saved session | *Your session has expired. Please log in again.* |
| Invalid email | *Please enter a valid email address.* |
| Password mismatch | *Passwords do not match.* |
| Password too short | *Password must be at least 6 characters.* |
| Empty identifier / password / institution code | *Please enter your email, register number, or university roll number.* / *Please enter your password.* / *Please enter your institution code to sign in with a register number or roll number.* |
| Backend / network failure | *The server reported an error. Please try again later.* / *Could not reach the backend. Please make sure the server is running.* |
| Dev feature disabled | *This development-only feature is disabled.* |
| Unexpected recovery failure | *We could not complete the password reset. Please try again.* |

**Unification applied:** `services/auth.ts` `session_invalid` previously said
*"The saved session could not be verified. Please sign in again."* — a second
sentence for the same event. It now returns `SESSION_EXPIRED_MESSAGE` from
`services/sessionEvents.ts`, so restore-time expiry and mid-session expiry use
one identical string. Rejected credentials remain a *different*, clearly
distinct message (asserted by test).

Never surfaced: SQL/DB errors, stack traces, exception or constraint names, JWT
details, recovery details, internal identifiers, or raw backend messages — and
`services/devAuth.ts` `user_not_found` no longer reads *"No account was found
for that email."* either (defence in depth at the client).

---

## 9. Loading States

| Operation | Label | Guards |
|---|---|---|
| Login | `Signing in…` | `status === 'authenticating'`; every input and every visibility toggle disabled; duplicate submits blocked |
| Registration | `Creating account…` | `submitting`; all inputs disabled |
| Institution lookup | `Finding institution…` (live region) | `checking`; submit refused until resolved |
| Password reset | `Resetting password…` | `busy`; duplicate submits blocked |
| Change password | `Updating…` (was `Changing…`) | `busy`; duplicate submits blocked |

Every form also exposes `aria-busy` while its operation is in flight, and the
in-flight guards run before any request is created, so a second click cannot
produce a second request.

---

## 10. Accessibility

| Requirement | Status |
|---|---|
| Every input has a proper label | ✅ — wrapped labels (login/registration) or explicit `htmlFor`/`id` (`PasswordField`, recovery email) |
| Errors associated with fields | ✅ — `aria-invalid` + `aria-describedby` pointing at the message element; login keeps its single form-level alert (`role="alert"`) because that is the existing screen architecture |
| `role="alert"` used appropriately | ✅ — form-level failures and field errors; `role="status"` for success/loading text |
| Keyboard navigation | ✅ — visibility toggles are real buttons (`Tab` + `Enter`/`Space`), no click-only control added |
| Logical focus order | ✅ — unchanged DOM order: identifier → institution code → password (+ toggle) → submit |
| Meaningful button names | ✅ — `Sign in`, `Register as Student`, `Reset password`, `Change password`, `Show/Hide <field>` |
| Password visibility controls accessible | ✅ — state-dependent accessible name, `aria-controls`, disabled with the input |
| Loading communicated | ✅ — button label change + `aria-busy` + disabled controls |
| Colour is not the only error indicator | ✅ — every error is text in an alert region; success is text in a status region |
| Submission without a mouse | ✅ — all flows are plain `<form>` submits |
| No new a11y dependency introduced | ✅ — no library added |

Dev-only panel toggle (`App.tsx`) also gained `aria-expanded` + `aria-controls`.

---

## 11. Mobile UX

Verified against the existing responsive structure (no layout rewrite):

* Every auth screen is a single column, `max-w-md w-full` inside `px-4`, so the
  card never exceeds the viewport; long error text wraps inside its container.
* Inputs remain full-width and usable at small widths; the password toggle is a
  `shrink-0` sibling (never overlapping or clipping the value) and every input
  keeps `min-w-0`.
* Buttons are full-width or block-level with adequate padding/tap targets.
* No horizontal overflow was introduced (no fixed widths, no absolutely
  positioned controls, no `overflow-x` add-ons).
* `autoComplete` attributes are preserved (`username`, `current-password`,
  `new-password`, `email`, `name`) so mobile password managers/keyboards behave.
* Recovery and change-password screens scroll normally, keeping Submit / Back to
  Login reachable above the on-screen keyboard (top-aligned single-column card).

---

## 12. Security Verification

| Check | Result |
|---|---|
| Passwords never appear in logs | ✅ — no `console.*`/logger call in any auth form; passwords only pass through `JSON.stringify` in the request body |
| Tokens never appear in logs | ✅ — unchanged (Phase 6.15.4/6.15.5 behaviour) |
| Recovery details not exposed | ✅ — no token exists; the success copy carries no account information |
| Passwords never placed in URLs | ✅ — recovery/change/login bodies only; institution lookup uses a query string with a *code*, never a password |
| Forgot-password enumeration prevented | ✅ — backend response parity for known/unknown email **+** client copy that never confirms existence (tested) |
| Login enumeration prevented | ✅ — unchanged: `400/401 INVALID_CREDENTIALS` for every denial |
| Registration errors remain safe | ✅ — unchanged controlled messages (pre-existing tests still pass) |
| Session-expiry behaviour remains safe | ✅ — protected-API 401 → `session_invalid` → clear state + token → login UI with the shared sentence |
| Login 401 vs session 401 remain separate | ✅ — `invalid_credentials` vs `session_invalid` classification untouched; asserted |
| Role resolution remains server authoritative | ✅ — `App.tsx` still selects the shell from `user.role`; no client-side role logic added |
| Tenant isolation unchanged | ✅ — no tenancy code touched |
| Password state clearing | ✅ — registration, reset and change-password all drop plaintext values when the request settles; storage audit tests still pass |
| No password in localStorage/sessionStorage/URLs | ✅ — asserted by tests (storage lengths 0 after recovery; unchanged registration test) |

---

## 13. Tests Added

**Frontend (new file)**

* `frontend/src/features/auth/PasswordField.test.tsx` (7 tests) — label
  association, independent visibility toggle with value preserved, keyboard
  operation, `aria-invalid`/`aria-describedby` wiring, no-attributes-when-valid,
  disabled state, no plaintext rendering outside the input.

**Frontend (extended)**

* `LoginForm.test.tsx` +7 — visibility toggle (and its disabled state while
  signing in), empty identifier, missing institution code, short password,
  validation message cleared on edit, shared session-expiry message rendering.
* `RegistrationForm.test.tsx` +1 — independent per-field visibility toggle.
* `ForgotPasswordForm.test.tsx` (rewritten, 17 tests) — rendering; email-only
  recovery (no register/roll/institution code); empty-field, invalid-email,
  short-password and mismatch validation; error association + clearing;
  generic anti-enumeration outcome; no authentication and no credential
  persistence; no account-existence wording for an unexpected `user_not_found`;
  server-error and dev-disabled messages; `Resetting password…` + duplicate
  prevention; back-to-login from both states; visibility toggle.
* `ChangePasswordForm.test.tsx` (rewritten, 9 tests) — rendering; missing
  current password; short new password; mismatch; successful update clearing all
  three plaintext fields while keeping the session (no `logout`); rejected
  current password; undetermined account email; `Updating…` + duplicate
  prevention; single-field visibility toggle.
* `services/auth.test.ts` +2 — the `session_invalid` message equals
  `SESSION_EXPIRED_MESSAGE`; rejected credentials stay distinct from expiry.

**Backend**

* `tests/test_dev_auth.py` — `test_forgot_password_user_not_found` (which
  asserted the enumerating `404 USER_NOT_FOUND`) was replaced by
  `test_forgot_password_does_not_reveal_account_existence`, asserting status +
  body parity between a known and an unknown email, no password update for the
  unknown email, and the absence of account-existence wording. The success test
  now asserts the generic message.

---

## 14. Test Results

| Command | Result |
|---|---|
| `npm test` (frontend, vitest) | **189 passed / 189**, 17 files (baseline 154/16 → +35 tests) |
| `python -m pytest tests -q` (backend) | **1616 passed, 15 skipped** — identical to the Phase 6.15.5 baseline (the 15 skips are the pre-existing live-database manual skips) |
| `python -m pytest tests/test_dev_auth.py -q` | 15 passed |
| `npx tsc -b` (typecheck) | 0 errors |
| `npm run build` (`tsc -b && vite build`) | success — see §17 |
| `python -m pytest -q` (repo root scope) | **not applicable**: pytest also discovers `scripts/manual_tests/*`, which require a live HTTP server (`httpx.ConnectError`) and abort collection. Pre-existing condition; the suite is run as `pytest tests`, as in Phases 6.14.x/6.15.5. |

Pre-existing warnings (documented, not introduced here): `act(...)` warnings in
`AdminShell.test.tsx`; Vitest jsdom-environment notice; Starlette/FastAPI
deprecation warnings; `PytestCollectionWarning` for `TestResult*` Pydantic
models.

---

## 15. Files Changed (Phase 6.15.6 only)

**New**

| File | Purpose |
|---|---|
| `frontend/src/features/auth/PasswordField.tsx` | Shared accessible password input with visibility toggle |
| `frontend/src/features/auth/PasswordField.test.tsx` | Component contract tests |
| `PHASE_6_15_6_AUTH_UX_RECOVERY.md` | This document |

**Modified (frontend)**

| File | Change |
|---|---|
| `features/auth/LoginForm.tsx` | Client-side validation (identifier / institution code / password), `noValidate`, single alert region (`fieldError ?? error`), `PasswordField`, `aria-busy`, removed the stale Phase 5.4 footer |
| `features/auth/RegistrationForm.tsx` | `PasswordField` for both password inputs, `aria-busy` (contract untouched) |
| `features/auth/ForgotPasswordForm.tsx` | Reworked UX on the unchanged endpoint: login-screen card/layout, per-field validation, generic anti-enumeration success + failure copy, `Resetting password…`, `aria-busy`, `Back to Login` |
| `features/auth/ChangePasswordForm.tsx` | `PasswordField` ×3, per-field validation, `Updating…`, `aria-busy`, explicit "session stays active" success text |
| `services/auth.ts` | `session_invalid` now returns the shared `SESSION_EXPIRED_MESSAGE` |
| `services/devAuth.ts` | `user_not_found` message made generic (no account-existence disclosure) |
| `App.tsx` | `aria-expanded` + `aria-controls` on the dev change-password toggle |
| `features/auth/LoginForm.test.tsx`, `RegistrationForm.test.tsx`, `ChangePasswordForm.test.tsx`, `ForgotPasswordForm.test.tsx`, `services/auth.test.ts` | Tests listed in §13 |

**Modified (backend)**

| File | Change |
|---|---|
| `app/api/dev_auth.py` | `dev_forgot_password` returns one generic `200` response for a known and an unknown email (`_GENERIC_RECOVERY_MESSAGE`); no password change for an unknown email. Dev/TEST-only endpoint; `change-password` and the admin reset endpoint are unchanged |
| `tests/test_dev_auth.py` | Enumeration test replaced by the parity test; success test asserts the generic message |

---

## 16. Known Limitations

1. **No email/token recovery exists.** Password recovery is only available with
   `DEV_TEST_MODE=true`, and it applies the new password immediately (no email is
   sent). A reset-link flow would require a new backend endpoint and is out of
   scope for this phase (explicitly not invented).
2. **Generic recovery response hides typos in development.** Because a known and
   an unknown email are indistinguishable by design, a mistyped address in the
   dev tool reports the same generic sentence as a successful reset. This is the
   intended, production-grade anti-enumeration behaviour.
3. **Password change does not revoke the existing session.** A changed password
   keeps currently issued JWTs valid until they expire (no revocation endpoint
   exists). Documented, not changed: session revocation would be an architecture
   change.
4. **Login keeps one form-level alert** instead of per-field messages, matching
   the existing screen architecture; the password-recovery screens use
   per-field messages. `RegistrationForm` likewise keeps its existing
   message-per-check pattern.
5. **Visual/mobile checks are structural + jsdom-verified.** There is no
   browser/device automation in this repository, so small-viewport review was
   performed by inspecting the committed responsive classes (single column,
   `max-w-md`, `px-4`, flex-based toggle, no fixed widths) rather than by
   screenshot tooling.
6. **Student accounts whose `/auth/me` email is `null`** cannot use the dev
   change-password convenience; the form reports the safe message *"Your account
   email could not be determined. Please sign in again."* (the endpoint is
   email-keyed).
7. Pre-existing, unchanged: `act(...)` warnings in `AdminShell.test.tsx`; the
   Tailwind/lightningcss `::file-selector-button:disabled` warning during
   `vite build` (present in the Phase 6.15.5 build log too).
8. `pytest` must be run as `pytest tests` — a root-level `pytest` also collects
   `scripts/manual_tests/*`, which need a live server (pre-existing).

---

## 17. Final Verification

| Command | Result |
|---|---|
| `npm test` | 189 passed / 189 (17 files) — 0 failures |
| `npx tsc -b` | 0 TypeScript errors |
| `npm run build` | success — `dist/index.html` 0.42 kB, `dist/assets/index-BpJkRfj9.css` 26.74 kB, `dist/assets/index-DH8MMVWq.js` 283.20 kB (63 modules, built in 2.78 s) |
| `python -m pytest tests -q` | 1616 passed / 15 skipped — 0 failures |
| `python -m pytest tests/test_dev_auth.py -q` | 15 passed |
| Regression surface | `auth.test.ts`, `AuthProvider.test.tsx`, `App.test.tsx`, `AdminShell.test.tsx`, `adminApi.test.ts`, `api.test.ts`, `devAuth.test.ts`, `registration.test.ts`, backend `test_auth.py`, `test_student_auth_phase_6_5.py`, `test_sign_in_phase_6_13_6.py`, RBAC/tenancy suites — all pass unchanged |

### Definition of Done

| Item | Status |
|---|---|
| Forgot-password architecture audited | ✅ (§2) |
| Forgot-password UI verified/improved | ✅ (§3) |
| Account enumeration prevented | ✅ (backend parity + client copy, tested) |
| Password reset flow verified | ✅ (§4 — no token flow exists; documented) |
| Change-password flow verified | ✅ (§5) |
| Password validation verified | ✅ (§6) |
| Password state clearing verified | ✅ (§9/§12, tested) |
| Password visibility verified/implemented | ✅ (`PasswordField`, §7) |
| Authentication errors standardized | ✅ (§8) |
| Loading states verified | ✅ (§9) |
| Duplicate submissions prevented | ✅ (tested for every screen) |
| Accessibility reviewed | ✅ (§10) |
| Mobile UX reviewed | ✅ (§11) |
| Authentication navigation verified | ✅ (Login↔Register, Login↔Forgot, Authenticated↔Change) |
| Password-change session behaviour verified | ✅ (§5 — session stays valid) |
| Registration compatibility verified | ✅ (registration tests unchanged and passing) |
| Session-expiry compatibility verified | ✅ (AuthProvider/App tests unchanged and passing) |
| Security regression verified | ✅ (§12) |
| Frontend tests pass | ✅ 189/189 |
| Backend tests pass | ✅ 1616 passed / 15 pre-existing skips |
| Typecheck passes | ✅ 0 errors |
| Production build passes | ✅ |
| Documentation created | ✅ (this file) |
| Git scope reviewed | ✅ (below) |
| No unrelated changes introduced | ✅ |

---

## Git Scope Verification

`git status` before and after this phase shows the same pre-existing uncommitted
content from Phases 6.15.1–6.15.5 (17 modified files and 14 untracked files — the
17/13 listed in `PHASE_6_15_5_AUTH_E2E_QA.md` plus that phase's own document).

Measured working tree after Phase 6.15.6: **24 modified, 17 untracked**. The
delta attributable to this phase is:

* `PHASE_6_15_6_AUTH_UX_RECOVERY.md` (new, untracked)
* `frontend/src/features/auth/PasswordField.tsx` (new, untracked)
* `frontend/src/features/auth/PasswordField.test.tsx` (new, untracked)
* Edits inside files that were **already modified** by earlier phases
  (`App.tsx`, `LoginForm.tsx`, `services/auth.ts`, `backend/app/api/dev_auth.py`)
  plus edits inside files that were **already untracked**
  (`RegistrationForm.tsx`, `RegistrationForm.test.tsx`, `auth.test.ts`) and
  files that were committed clean before this phase
  (`ForgotPasswordForm.tsx`, `ForgotPasswordForm.test.tsx`,
  `ChangePasswordForm.tsx`, `ChangePasswordForm.test.tsx`,
  `LoginForm.test.tsx`, `services/devAuth.ts`, `backend/tests/test_dev_auth.py`).

Git cannot attribute individual hunks inside files that were already dirty or
untracked; §15 records the exact 6.15.6 delta. Nothing was committed, and no
Phase 6.15.7 work was started.

**PHASE 6.15.6 — COMPLETE.**

