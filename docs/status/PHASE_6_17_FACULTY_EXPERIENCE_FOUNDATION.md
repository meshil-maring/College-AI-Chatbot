# Phase 6.17 — Faculty Experience & Academic Workspace Foundation

## 1. Phase Objective

Establish the first dedicated, authenticated **Faculty Experience** for the
College AI Chatbot: a `FacultyShell` with faculty-specific navigation and a
faculty dashboard, built exclusively on **server-authoritative** contracts
that already exist after Phase 6.15 (authentication/roles) and Phase 6.16
(student experience).

The phase is the beginning of the Faculty Experience milestone. Faculty no
longer falls back to the student shell, while student and admin behaviour
remain byte-for-byte intact, and every faculty capability is verified against
the backend before it is rendered.

## 2. Strict Scope

Worked on:

- Faculty role audit, faculty authorization audit
- `FacultyShell`, faculty navigation, faculty dashboard
- Faculty identity/context presentation
- Faculty academic workspace foundation (verified capabilities only)
- Faculty AI Assistant entry point (existing `ChatShell`)
- Loading/empty/error discipline, session lifecycle reuse, tenant isolation,
  ownership/scoping verification, data minimization, accessibility,
  responsive behaviour
- Frontend tests, backend authorization/security tests, full regression,
  documentation (`PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md`)

Explicitly NOT implemented (out of scope):

- Staff dashboard/workflow, admin redesign, mobile application
- Faculty payroll, HR, messaging, notifications
- Student profile editing, new authentication, OAuth, refresh tokens
- New RAG architecture, chatbot redesign, payment system
- Any new faculty attendance/results/notices/resources mutation endpoint
- Phase 6.18 / Staff Experience (not started)

No commit was created automatically; git scope is documented in section 34.

## 3. Locked Architecture

The following contracts were treated as frozen and are unchanged:

```
Authentication
    Supabase Auth -> JWT -> get_current_user -> public.users
                -> user_roles -> server-authoritative role

Tenant resolution
    authenticated user -> institution/tenant resolution
                       -> tenant-scoped academic data

Roles (unchanged): admin | staff | faculty | student
```

Key primitives reused verbatim (no modification):

| Primitive | File | Reuse |
|---|---|---|
| `get_current_user` | `backend/app/core/security.py` | identity always server-side |
| `require_roles(*allowed)` | `backend/app/core/security.py` | 401/403 on every privileged route |
| `resolve_primary_role` | `backend/app/core/security.py` | canonical role for `/auth/me` |
| `scope_tenant` / `assert_tenant_object` / `user_tenant_id` | `backend/app/core/security.py` | 403 `TENANT_MISMATCH` isolation |
| `get_student_context` | `backend/app/services/student_context.py` | student-only identity chain (fails closed for faculty) |
| `AuthProvider` / `notifySessionExpired` | `frontend/src/features/auth`, `frontend/src/services/sessionEvents.ts` | Phase 6.15 session lifecycle |

No new role, no new authorization rule, no second role-detection request.

## 4. Faculty Role Audit

Audit performed over `backend/app/core/security.py`, `backend/app/api/*`,
`backend/app/services/*`, `backend/app/schemas/*`, `backend/app/models/*`,
`backend/tests/*`, `frontend/src/App.tsx`, `frontend/src/features/*`,
`frontend/src/services/*`, `frontend/src/types/*`.

Findings (all verified against code + existing tests):

1. **Role resolution** — `SUPPORTED_ROLES = ("admin", "staff", "faculty",
   "student")`; `resolve_primary_role` returns `"faculty"` for a
   faculty-only account (precedence admin > staff > faculty > student).
   `GET /api/v1/auth/me` already returned `role: "faculty"`
   (`tests/test_auth.py::test_auth_me_returns_faculty_role`).
2. **Faculty has NO academic profile** — there is no faculty table, no
   faculty department/subject/assignment model anywhere in
   `backend/app/models`, `services`, `repositories`, or the schema set.
   The string `faculty_id` appears NOWHERE in the codebase.
3. **Faculty has NO faculty-to-student scope** — no assignment, class,
   subject or department link exists that would define which students a
   faculty member may see.
4. **Faculty chat** — `/api/v1/conversations` and the generation chat route
   authenticate with plain `get_current_user` (any authenticated role);
   the personalized-chat pipeline routes faculty down the existing
   non-student path (`tests/test_personalized_chat_6_14_7.py`:
   `test_15b_faculty_general_question_has_no_student_context`).
5. **Faculty ingestion** — `/documents/ingest|extract|chunk|embed` are
   authorized with `require_roles("admin", "staff", "faculty")` plus
   `assert_tenant_object` tenant checks
   (`tests/test_ingestion.py::test_ingest_faculty_is_allowed`).
6. **Faculty attendance** — every `/admin/*attendance*` route is
   `require_roles("admin")`; faculty gets 403
   (`tests/test_attendance_phase_6_7.py::test_faculty_cannot_manage_attendance`).
7. **Faculty on student surfaces** — `/students/me/*` resolve the student
   identity server-side (`users.user_id -> students.user_id`). A faculty
   account has no `students` row, so every `/students/me/*` call fails
   closed with `404 STUDENT_PROFILE_NOT_FOUND`
   (`backend/app/services/student_context.py`).
8. **Faculty notices/resources** — the only read paths are
   `/students/me/notices`, `/students/me/resources` (student identity chain
   => 404 for faculty) and `/admin/notices`, `/admin/knowledge-sources`
   (`require_roles("admin")` => 403 for faculty). Faculty therefore has NO
   authorized notices/resources read contract.
9. **Faculty results** — `/admin/results*`, `/admin/test-results*`,
   `/admin/students/{id}/results` are all `require_roles("admin")` => 403.
10. **Pre-6.17 shell behaviour** — `App.tsx` routed `faculty` (and `staff`)
    into `StudentShell` as an explicit, documented fallback.

Conclusion: before this phase, faculty had exactly three verified
capabilities: **authenticated identity (`/auth/me`)**, **the AI Assistant**,
and **the document-ingestion pipeline** (backend-authorized, but with no
faculty-facing knowledge-source listing contract, hence no UI surface).

## 5. Faculty Authorization Matrix

Evaluated strictly from the backend contracts (nothing assigned to fill the
table; "contract-dependent" cells were resolved by audit):

| Capability | Student | Faculty | Staff | Admin | Faculty verdict basis |
|---|---|---|---|---|---|
| Own profile (/auth/me) | ✓ | ✓ | ✓ | ✓ | `role: "faculty"` + tenant resolved server-side |
| Student dashboard | ✓ | ✗ | ✗ | ✗ | `/students/me/*` -> 404 `STUDENT_PROFILE_NOT_FOUND` |
| Faculty dashboard | ✗ | ✓ | ✗ | ✗ | Phase 6.17 UI over verified identity/capabilities only |
| View own academic identity | ✓ | ✓ (limited) | ✓ | ✓ | email + role + tenant status only; no faculty profile exists |
| View student attendance | own only | ✗ | contract-dependent | ✓ | `/admin/*attendance*` -> 403 |
| Modify attendance | ✗ | ✗ | ✗ | ✓ | `require_roles("admin")`; 403 pinned by Phase 6.7 + 6.17 tests |
| View student results | own only | ✗ | contract-dependent | ✓ | `/admin/results*` -> 403 |
| Modify results | ✗ | ✗ | contract-dependent | ✓ | `require_roles("admin")` -> 403 |
| Manage students / approvals | ✗ | ✗ | ✓ (existing) | ✓ | `_APPROVAL = require_roles("admin", "staff")`; faculty NOT included -> 403 |
| Notices (view) | ✓ own institution | ✗ | contract-dependent | ✓ | `/students/me/notices` -> 404; `/admin/notices` -> 403 |
| Notices (create/publish/delete) | ✗ | ✗ | contract-dependent | ✓ | admin-only -> 403 |
| Learning resources (view) | ✓ own institution | ✗ | contract-dependent | ✓ | `/students/me/resources` -> 404; `/admin/knowledge-sources` -> 403 |
| Learning resources (upload pipeline) | ✗ | ✓ backend-authorized | ✓ | ✓ | `require_roles("admin","staff","faculty")` on `/documents/*`; NO faculty-facing listing contract, so no faculty upload UI this phase |
| AI Assistant | ✓ | ✓ | ✓ | ✓ | `get_current_user`; faculty non-student chat path (tested) |
| Admin functions | ✗ | ✗ | ✗ | ✓ | `require_roles("admin")` |

**Explicitly unsupported for faculty (documented, not granted):** student
visibility, student lists, attendance read/write, results read/write,
notices read/manage, learning-resource read/upload UI, admin functions.
These remain unavailable until the backend introduces an explicit
faculty-scoping contract.

## 6. Faculty Role Resolution

Verified and reused — not re-implemented:

- `GET /api/v1/auth/me` resolves `role = "faculty"` server-side from the
  JWT -> `public.users` -> `user_roles` -> `roles` chain.
- The frontend consumes ONLY `AuthProvider` state (`user.role` from
  `/auth/me`). No second faculty probe, no `/admin/me`, no
  email/identifier/localStorage inference.
- Precedence for multi-role accounts is unchanged
  (`admin > staff > faculty > student`).
- Pinned by `tests/test_faculty_experience_phase_6_17.py`:
  `test_resolve_primary_role_returns_faculty`,
  `test_auth_me_returns_faculty_role_with_tenant`,
  `test_auth_me_faculty_multi_role_precedence_unchanged`.
- Frontend: `frontend/src/App.test.tsx` verifies `role = 'faculty'`
  selects `FacultyShell`.

## 7. FacultyShell

New file: `frontend/src/features/faculty/FacultyShell.tsx`.

- Selected in `App.tsx` from the server-authoritative role:
  `role === 'faculty'` -> `FacultyShell` (`staff` and `student` unchanged ->
  `StudentShell`; `admin` unchanged -> `AdminShell`; unknown/`null` ->
  fail-safe restricted shell).
- Reuses `AuthProvider` identity and the existing `ChatShell` — no duplicated
  chat/session/token/role handling.
- Layout follows the established shell pattern (header + labelled nav +
  main), with `overflow-x-clip` and `min-w-0` guards so no page-level
  horizontal overflow occurs.
- Defensive neutral state: if an authenticated session somehow has no
  identity payload, the shell renders a controlled
  "Faculty workspace unavailable" state with sign-out instead of partial data.

## 8. Faculty Navigation

New file: `frontend/src/features/faculty/facultyNavigation.ts`.

Rendered navigation (verified capabilities only):

```
Dashboard    -> FacultyDashboard (identity + verified capability map)
AI Assistant -> existing ChatShell
Profile      -> FacultyProfile (safe identity)
```

- `buildFacultyNavigation(role)` returns items ONLY for `role === 'faculty'`;
  every other role (student/staff/admin/`null`/unknown) gets an EMPTY
  navigation — fail-safe.
- The navigation contains **no** admin, user-management, role-management, or
  institution-administration entries, and no Students/Attendance/Results/
  Notices/Resources entries, because no server-authorized faculty contract
  exists for those surfaces. Fake pages were NOT created to fill navigation.
- UX only, never authorization: the backend rejects any manually-requested
  privileged URL (403/404, pinned by the Phase 6.17 backend suite).

## 9. Faculty Dashboard

New file: `frontend/src/features/faculty/FacultyDashboard.tsx`.

Structure:

```
Faculty identity        (server-verified /auth/me fields only)
Academic workspace      (verified capability map — availability only)
Ask the AI Assistant    (entry point -> existing ChatShell)
```

- The workspace section renders `FACULTY_WORKSPACE_SURFACES`: the AI
  Assistant is marked **Available**; Students / Attendance / Results /
  Notices / Learning Resources are marked **Not available yet** with neutral
  wording — a UI mirror of the server authorization matrix, NOT fabricated
  data.
- No student counts, subject counts, attendance percentages, result
  statistics, or department information are invented: none of them has an
  authorized faculty backend source.
- A "Recent Notices" section is intentionally absent — faculty has no
  notice-read contract (see section 16).

## 10. Faculty Identity

New file: `frontend/src/features/faculty/FacultyIdentityCard.tsx`.

Rendered (actual backend fields only):

- **Email** — from `/auth/me`
- **Role** — "Faculty" (from `/auth/me role`)
- **Institution** — presence only ("Linked to your institution" / "No
  institution linked"); the internal tenant UUID is never rendered
- **Department** — explicit honest placeholder ("Not provided by your
  institution yet") because no faculty department field exists

Never rendered: `user_id`, `auth_user_id`, `institution_id` values, JWT,
service metadata, or any internal audit field. Full name and faculty
identifier are not rendered because the backend does not provide them.

## 11. Faculty Academic Context

The backend provides **no faculty academic profile**: no faculty table, no
department, program, discipline, subject, academic year or semester
association exists for faculty accounts. Therefore:

- Nothing is invented. The Profile page states honestly that the institution
  has not linked academic context to faculty accounts yet.
- No faculty-specific "current semester" algorithm was created.
- When a faculty academic profile contract is introduced by the backend, the
  `FacultyProfile` page is the single integration point.

## 12. Faculty Student Visibility

**Critical security boundary — no contract exists.**

- There is no faculty-to-student scope (no assigned subject/class/
  department/academic-context link) anywhere in the backend. A
  faculty-to-student scope was **NOT invented**.
- Faculty requests against every student surface fail closed server-side:
  `/students/me/*` -> `404 STUDENT_PROFILE_NOT_FOUND`; `/admin/students*` ->
  `403 FORBIDDEN`.
- Pinned by `tests/test_faculty_experience_phase_6_17.py`
  (`test_faculty_cannot_read_*`, `test_faculty_denied_admin_student_list`,
  `test_faculty_denied_admin_pending_students`).
- Client-supplied `?faculty_id=` / `?student_id=` / `?institution_id=` do not
  exist as authorization mechanisms anywhere; the Phase 6.17 suite proves a
  client-supplied `institution_id`/`student_id` query cannot widen a faculty
  request (`test_faculty_identity_parameters_cannot_widen_student_scope`).

## 13. Faculty Student List

**Not implemented — no authorized endpoint exists.** A broad
institution-wide student list was explicitly NOT created. Per section 12,
no faculty student-list surface or navigation entry exists. The dashboard's
"Students" card renders "Not available yet" with neutral wording.

## 14. Faculty Attendance Access

Audit outcome: **read-only/unavailable — no faculty contract exists.**

- View attendance: DENIED. `/admin/*attendance*` is
  `require_roles("admin")` (403); `/students/me/attendance*` is the
  student-only identity chain (404 for faculty).
- Record/modify attendance: DENIED. Pinned by
  `test_faculty_cannot_manage_attendance` (Phase 6.7) and
  `test_faculty_denied_admin_attendance_create` (Phase 6.17).
- No mutation endpoint was created for this phase. The dashboard's
  "Attendance" card renders "Not available yet".

## 15. Faculty Results Access

Audit outcome: **unavailable — no faculty contract exists.**

- View student/subject results: DENIED (`/admin/results*`,
  `/admin/test-results*`, `/admin/students/{id}/results*` all
  `require_roles("admin")` -> 403; `/students/me/results*` -> 404).
- Create/update/delete results: DENIED (same 403 boundary).
- Faculty is not authorized to modify results; no mutation path exists or
  was added. The dashboard's "Results" card renders "Not available yet".

## 16. Faculty Notices

Audit outcome: **view unavailable — no faculty read contract exists.**

- `/students/me/notices` (student identity chain) -> 404 for faculty.
- `/admin/notices` (`require_roles("admin")`) -> 403 for faculty.
- Create/edit/publish/delete notices: admin-only -> 403; publication
  privileges were NOT granted based on the faculty role.
- The dashboard intentionally renders no "Recent Notices" section —
  there is no authorized data source to display.

## 17. Faculty Learning Resources

Audit outcome: **view unavailable for UI — no faculty read contract exists.**

- `/students/me/resources` -> 404; `/admin/knowledge-sources` -> 403.
- Upload pipeline (`/documents/ingest|extract|chunk|embed`) IS
  faculty-authorized (`require_roles("admin", "staff", "faculty")` with
  `assert_tenant_object` tenant checks), but there is no faculty-facing
  knowledge-source listing contract to select a target
  `knowledge_source_id`, so NO upload UI was built (a UI would require
  inventing an API response shape).
- No storage internals are exposed anywhere in the faculty UI.

## 18. Faculty AI Assistant

Integrated — existing `ChatShell` reused verbatim:

- Faculty is authorized on `/api/v1/conversations` and the generation chat
  route via the plain `get_current_user` dependency (any authenticated
  role), with the existing non-student personalization path
  (`test_15b_faculty_general_question_has_no_student_context`).
- No second chatbot, no faculty-specific RAG architecture, no change to the
  generation pipeline.
- Limitation documented: the existing AI context builder does not yet inject
  faculty-specific personalization (faculty follows the general
  non-student path). No faculty data is injected into prompts from the
  frontend.

## 19. Loading States

- The shell renders only after `/auth/me` has authenticated the session
  (`AuthProvider` `status === 'authenticated'`), so no faculty section can
  render a fabricated mid-load or "0" value while a request is in flight.
- Phase 6.17 introduces NO async data sections (no faculty data contract
  exists to load), so there are no loading spinners to fake; the four-state
  discipline (idle/loading/loaded/error) of `useStudentResource` remains the
  pattern any future faculty section must follow.

## 20. Empty States

- The workspace overview uses neutral, non-failure wording:
  "Not available yet" / "not available for faculty accounts yet".
- The academic-context profile states honestly that the institution has not
  linked academic context yet.
- No state implies a system failure when the authorized dataset is empty or
  absent.

## 21. Error Handling

- Faculty UI failures cannot destroy the application: the shell carries no
  async data section, and any future section must isolate its own error
  state per section with section-level retry (the `useStudentResource`
  pattern), so one failing section never blanks the rest.
- A normal API failure does NOT log the faculty member out; only a genuine
  401 raises the existing Phase 6.15 `notifySessionExpired` ->
  `AuthProvider` -> login flow.
- No faculty-specific session handling was created.

## 22. Tenant Isolation

Mandatory server-side boundary, verified by the Phase 6.17 suite:

- Faculty A (Institution A) CAN reach only Institution-A-scoped authorized
  surfaces (`test_faculty_ingest_allowed_for_own_tenant`).
- Faculty A (Institution A) CANNOT reach Institution B data
  (`test_faculty_ingest_denied_for_cross_tenant_knowledge_source` -> 403
  `TENANT_MISMATCH`).
- `/auth/me` returns the faculty tenant resolved server-side
  (`test_auth_me_returns_faculty_role_with_tenant`).
- Frontend filtering plays no part in isolation; the faculty UI renders no
  tenant-controlled query anywhere.

## 23. Faculty Ownership Isolation

- There is no faculty-owned academic data model (no assigned students,
  subjects, or classes), so no ownership surface exists to expose.
- The contract map guarantees faculty cannot reach ANOTHER faculty member's
  (or any) student data: no endpoint accepts a client-supplied
  `?faculty_id=` and every student surface is identity-chain or admin-gated.
- Cross-faculty restricted-data access is structurally impossible in the
  current contract set and is pinned by the denial tests in sections 12–16.

## 24. Student Data Minimization

- The faculty UI renders NO student data at all (no authorized contract).
- No internal identifiers (`user_id`, `auth_user_id`, `institution_id`
  values), tokens, or service metadata are rendered anywhere in the faculty
  shell — asserted by `FacultyDashboard.test.tsx`
  ("never renders internal identifiers or token material").
- Any future faculty student list must project only: name, register number,
  university roll number, program, year, section — never auth IDs, student
  UUIDs, credentials, or unrelated private data.

## 25. API Contract Discipline

Contract map produced from route + schema + service + authorization
dependency + tenant filter + test inspection (no response shape invented):

| Route | Authorization | Faculty outcome |
|---|---|---|
| `GET /api/v1/auth/me` | `get_current_user` | ALLOWED — role + tenant |
| `GET /api/v1/conversations` | `get_current_user` | ALLOWED — own conversations |
| `POST /api/v1/generation/chat` | `get_current_user` | ALLOWED — non-student path |
| `POST /api/v1/documents/ingest` (+ extract/chunk/embed) | `require_roles("admin","staff","faculty")` + `assert_tenant_object` | ALLOWED — tenant-scoped (no listing contract for UI) |
| `GET /api/v1/students/me/*` | `get_student_context` (student chain) | 404 `STUDENT_PROFILE_NOT_FOUND` |
| `GET /api/v1/admin/notices`, `/admin/knowledge-sources`, `/admin/students*`, `/admin/*attendance*`, `/admin/results*`, `/admin/test-results*`, `/admin/dashboard`, `/admin/me`, `/admin/audit-logs` | `require_roles("admin")` (approval: admin+staff) | 403 `FORBIDDEN` |

The faculty frontend calls ONLY `/auth/me`-derived state and the existing
chat services; no new API client shape was created.

## 26. Responsive Design

- Shell/dashboard use the same responsive utilities as the student shell
  (`flex-wrap` navigation, `sm:`/`lg:` grid breakpoints, `min-w-0` /
  `break-words` guards, `overflow-x-clip` on the page root) — no page-level
  horizontal overflow at mobile/tablet/desktop widths.
- Cards stack on mobile, two columns on `sm`, three on `lg`.
- No data table exists in the faculty UI; if future tables are added they
  must use table-level horizontal scrolling, not page-level.

## 27. Accessibility

- Semantic headings per view (`h1` page heading, `h2` section headings).
- `<nav aria-label="Faculty navigation">` landmark; content in `<main>`.
- Keyboard-operable buttons with visible `focus:ring` styles.
- Active navigation item announced via `aria-current="page"`.
- Sections labelled via `aria-labelledby` headings; the missing-identity
  state uses `role="status"`.
- Status conveyed by text ("Available" / "Not available yet"), never by
  color alone.

## 28. Frontend Tests

New test files:

- `frontend/src/features/faculty/facultyNavigation.test.ts` (6 tests) —
  navigation exists only for `faculty`; no admin/management labels; empty
  navigation for every other role (fail safe); capability map marks only the
  AI Assistant available.
- `frontend/src/features/faculty/FacultyShell.test.tsx` (8 tests) —
  FacultyShell renders the labelled faculty navigation; active state via
  `aria-current`; assistant view reuses `ChatShell`; profile navigation;
  controlled missing-identity state; sign-out; NO admin panel and NO student
  navigation.
- `frontend/src/features/faculty/FacultyDashboard.test.tsx` (5 tests) —
  identity renders safe fields; workspace surfaces render; AI assistant
  entry navigates; no internal IDs / token material in the DOM.
- `frontend/src/App.test.tsx` — updated: `role = 'faculty'` now selects
  `FacultyShell`; student/staff still select `StudentShell`; admin still
  selects `AdminShell`; unknown/`null` roles still fail safe.

## 29. Backend Tests

New file: `backend/tests/test_faculty_experience_phase_6_17.py` (26 tests).
NO production backend code was changed — the suite pins the existing
authorization contracts:

- Faculty role resolution (`/auth/me` role + tenant; precedence unchanged).
- Faculty denied on all student-only surfaces (profile, academic-profile,
  attendance, attendance summary, results, test-results, notices,
  resources) with `STUDENT_PROFILE_NOT_FOUND` — read-only enforcement where
  applicable.
- Client-supplied `institution_id`/`student_id` query parameters cannot
  widen a faculty request (invalid-identity-parameter rejection).
- Faculty denied (403 `FORBIDDEN`) on privileged endpoints: `/admin/me`,
  `/admin/dashboard`, `/admin/students`, `/admin/students/pending`,
  `/admin/students/{id}/approve`, `/admin/attendance` (create),
  `/admin/results` (create), `/admin/notices` (list + create),
  `/admin/knowledge-sources`, `/admin/audit-logs`.
- Faculty allowed on the chat surface (`/conversations`, scoped to the
  authenticated `user_id`).
- Faculty tenant isolation on the ingestion pipeline: own tenant allowed,
  cross-tenant `TENANT_MISMATCH`.
- No existing student/admin test was weakened or disabled.

## 30. Integration Tests

Faculty journey pinned by the suites above and the existing session tests:

```
Faculty authenticated (/auth/me -> role "faculty")
    -> FacultyShell (App.test.tsx)
    -> Dashboard (identity + verified capability map)
    -> AI Assistant (existing ChatShell, authorized by get_current_user)
    -> Logout (AuthProvider clearSession)
```

Cross-role denial (Phase 6.17 backend suite):

```
Faculty token  -> /students/me/*          -> 404 STUDENT_PROFILE_NOT_FOUND
Faculty token  -> /admin/*                -> 403 FORBIDDEN
Student token  -> /admin/* (require_roles("admin")) -> 403 (existing suites)
```

Student->admin and admin behaviour remain pinned by the existing Phase 6.6,
6.7, 6.8, 6.13.7, 6.15 and 6.16 suites (all green in the full regression).

## 31. Session Lifecycle

Reused Phase 6.15 behaviour verbatim — no faculty-specific session handling:

```
Faculty login  -> /auth/me (role "faculty") -> FacultyShell
Refresh        -> token restore -> /auth/me -> FacultyShell restored
API 401        -> notifySessionExpired(token) -> AuthProvider -> login
Logout         -> clearSession -> login screen
```

`FacultyShell` consumes the same `useAuth()` context as every other shell;
the cross-tab `storage` handler and token-scoped expiry notifications are
untouched.

## 32. Performance

- Faculty dashboard initial requests: **0** — the dashboard renders from
  `/auth/me` state already held by `AuthProvider`; there is no duplicate
  `/auth/me` call and no second role probe.
- Duplicate requests: none (no faculty data endpoint is called; the AI
  Assistant lazily mounts the existing `ChatShell` only when opened).
- Navigation requests: none (client-side view switching; the assistant view
  issues the chat requests the existing ChatShell already owns).
- Retry requests: none possible today (no async faculty section); the
  `useStudentResource` retry discipline is the mandated pattern for future
  sections.
- No speculative caching and no global state library were introduced.

## 33. Full Regression

Executed at the end of the phase (Windows, repo root):

| Gate | Command | Result |
|---|---|---|
| Backend | `python -m pytest tests -q` | **1840 passed, 15 skipped, 0 failed** |
| Frontend tests | `npx vitest run` | **37 files, 324 passed, 0 failed** |
| TypeScript | `npx tsc -b` | **OK (no errors)** |
| Production build | `npm run build` | **OK (`dist/` emitted, 83 modules)** |

All existing authentication, student, and admin suites remain green; no test
was disabled or weakened.

## 34. Phase Completion Status

| Requirement | Status |
|---|---|
| Faculty role resolution verified | ✓ (`/auth/me`, precedence pinned) |
| Faculty authorization matrix documented | ✓ (section 5) |
| FacultyShell implemented | ✓ (`FacultyShell.tsx`, wired in `App.tsx`) |
| StudentShell behaviour intact | ✓ (staff/student unchanged, tests green) |
| AdminShell behaviour intact | ✓ (unchanged, tests green) |
| Faculty navigation (verified capabilities only) | ✓ (Dashboard / AI Assistant / Profile) |
| Faculty dashboard implemented | ✓ |
| Faculty identity implemented | ✓ (safe fields only) |
| Faculty academic context implemented where available | ✓ (honestly absent — no backend contract) |
| Faculty student visibility contract verified | ✓ (fail-closed 404/403 pinned) |
| Faculty student list implemented only if authorized | ✓ — correctly NOT implemented (no endpoint) |
| Faculty attendance access verified | ✓ (denied; documented) |
| Faculty results access verified | ✓ (denied; documented) |
| Faculty notice access verified | ✓ (denied; documented) |
| Faculty resource access verified | ✓ (denied; ingestion pipeline authorized but no listing contract — documented) |
| Existing ChatShell integrated | ✓ |
| Loading / empty states implemented | ✓ (no fabricated async states; neutral wording) |
| Error/retry behaviour implemented | ✓ (per-section isolation pattern mandated; session expiry reused) |
| Tenant isolation verified | ✓ (403 `TENANT_MISMATCH` pinned) |
| Faculty ownership isolation verified | ✓ (no client-controlled identity params) |
| Student data minimization verified | ✓ (no internal IDs/tokens rendered; tested) |
| API contracts documented | ✓ (section 25) |
| Responsive behaviour verified | ✓ (shared shell utilities, overflow guards) |
| Accessibility verified | ✓ (landmarks, headings, focus, aria-current, status text) |
| Frontend tests pass | ✓ (324 passed) |
| Backend tests pass | ✓ (1840 passed, 15 skipped) |
| Integration tests pass | ✓ |
| Session lifecycle verified | ✓ (Phase 6.15 reused) |
| Performance reviewed | ✓ (0 dashboard requests) |
| Full regression passes | ✓ |
| TypeScript passes | ✓ |
| Production build passes | ✓ |
| Documentation contains exactly 34 sections | ✓ (this document) |
| Git scope documented / no unrelated changes / no commit | ✓ (see below) |

**Git scope (files changed/added by Phase 6.17):**

- Added: `backend/tests/test_faculty_experience_phase_6_17.py`
- Added: `frontend/src/features/faculty/FacultyShell.tsx`,
  `FacultyDashboard.tsx`, `FacultyIdentityCard.tsx`, `FacultyProfile.tsx`,
  `facultyNavigation.ts`, `facultyNavigation.test.ts`,
  `FacultyShell.test.tsx`, `FacultyDashboard.test.tsx`
- Modified: `frontend/src/App.tsx` (faculty shell selection + import),
  `frontend/src/App.test.tsx` (faculty expectation)
- Added: `PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md` (this document)

No backend production file was modified. No commit was created.

**STOP** — Phase 6.17 ends here. Phase 6.18 and the Staff Experience were
NOT started.
