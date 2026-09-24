# Phase 6.18 — Staff Experience & Operational Workspace Foundation

## 1. Phase Identity

- **Phase:** 6.18
- **Name:** Staff Experience & Operational Workspace Foundation
- **Status:** Implemented
- **Previous phase:** 6.17 — Faculty Experience & Academic Workspace Foundation
- **Primary objective:** Build the authenticated Staff experience using only
  capabilities and backend contracts that already exist.

The Staff experience is now a dedicated, server-authoritative workspace:
staff no longer falls back to the student shell, while student, faculty and
admin behaviour remain intact, and every staff capability is verified against
the backend before it is rendered.

## 2. Objective

Implement the first production-safe Staff workspace for the College AI
Chatbot:

- Resolve the Staff role server-authoritatively (`/auth/me`).
- Provide a dedicated `StaffShell` with a staff navigation model.
- Provide a useful Staff dashboard built only on real backend data/contracts.
- Reuse the existing authentication/session architecture unchanged.
- Preserve tenant isolation and role boundaries.
- Never expose admin-only functionality to Staff.
- Never invent Staff-specific academic or operational data models.
- Never bypass existing authorization.
- Leave capabilities without a backend contract documented and unavailable
  rather than inventing an API or UI.

## 3. Scope

Worked on:

- Staff role audit, staff authorization audit (capability matrix)
- `StaffShell`, staff navigation, staff dashboard, staff identity/profile
- Student approval queue workspace (`StaffApprovals`) — the one verified
  operational staff contract (Phase 6.4: `require_roles("admin", "staff")`)
- Staff AI Assistant entry point (existing `ChatShell`)
- Loading/empty/error discipline, session lifecycle reuse, tenant isolation,
  ownership/scoping verification, data minimization, accessibility,
  responsive behaviour
- Frontend tests, backend authorization/security tests, full regression,
  this documentation

Explicitly NOT implemented (no backend contract; documented, not granted):

- Student management UI (CRUD beyond the approval queue)
- Attendance, results, test-results, notices, FAQs, learning-resource and
  document management UIs (all admin-only, 403 for staff)
- User / role / institution management UIs
- Document upload UI (pipeline authorized, no listing contract — see §16)
- Any new backend endpoint, role, or permission
- Faculty or admin redesign, mobile application

## 4. Architecture Baseline

The following contracts were treated as frozen and are unchanged:

```
Authentication
    Supabase Auth -> JWT -> get_current_user -> public.users
                -> user_roles -> roles -> resolve_primary_role
                -> /auth/me -> AuthProvider -> StaffShell

Tenant resolution
    authenticated user -> institution/tenant resolution
                       -> tenant-scoped operational data

Roles (unchanged): admin | staff | faculty | student
```

Key primitives reused verbatim (no modification):

| Primitive | File | Reuse |
|---|---|---|
| `get_current_user` | `backend/app/core/security.py` | identity always server-side |
| `require_roles(*allowed)` | `backend/app/core/security.py` | 401/403 on every privileged route |
| `resolve_primary_role` | `backend/app/core/security.py` | canonical role for `/auth/me` |
| `scope_tenant` / `assert_tenant_object` / `user_tenant_id` | `backend/app/core/security.py` | 403 `TENANT_MISMATCH` isolation |
| `_approval_scope` | `backend/app/api/admin.py` | tenant-scoped approval authority (unchanged) |
| `get_student_context` | `backend/app/services/student_context.py` | student-only identity chain (fails closed for staff) |
| `AuthProvider` / `notifySessionExpired` | `frontend/src/features/auth`, `frontend/src/services/sessionEvents.ts` | Phase 6.15 session lifecycle |
| `requestJson` / `AdminApiError` | `frontend/src/services/adminApi.ts` | shared API client (401 -> session-expiry broadcast) |
| `ChatShell` | `frontend/src/features/chat` | AI Assistant surface (verbatim) |

No new role, no new authorization rule, no second RBAC system, no second
role-detection request.

## 5. Role Resolution

Verified server-authoritative flow (unchanged from Phase 6.15.4):

```
JWT -> get_current_user -> public.users -> user_roles -> roles
     -> resolve_primary_role() -> /auth/me -> AuthProvider -> StaffShell
```

- `SUPPORTED_ROLES = ("admin", "staff", "faculty", "student")`;
  precedence **admin > staff > faculty > student** is unchanged
  (pinned by `test_staff_multi_role_precedence_unchanged`).
- `GET /api/v1/auth/me` already returned `role: "staff"` for a staff-only
  account (`tests/test_auth.py::test_auth_me_returns_staff_role`), plus the
  tenant (`institution_id`) resolved server-side.
- Staff is selected ONLY when `role === "staff"` (in `App.tsx` and in
  `buildStaffNavigation`). Client-side role claims can never override the
  server role (pinned by
  `test_auth_me_client_role_claims_cannot_override_staff_role`).
- No `/admin/me` probe exists in the staff path (or anywhere in shell
  selection). No email/identifier/localStorage inference.

## 6. StaffShell

`frontend/src/features/staff/StaffShell.tsx`:

- Uses existing `AuthProvider` state (`user`, `role`, `accessToken`,
  `logout`) — no duplicated session logic.
- Displays staff identity using safe fields (email; role as "Staff").
- Renders staff navigation from `staffNavigation.ts` in
  `<nav aria-label="Staff navigation">` with `aria-current="page"`.
- Reuses the existing `ChatShell` verbatim inside a labelled section for the
  AI Assistant view.
- Renders a controlled neutral state ("Staff workspace unavailable" +
  sign-out) if the identity is somehow missing — never partial data.
- Avoids rendering internal UUIDs, JWTs or access tokens.
- Contains no admin functionality and no student-shell fallback.

## 7. Navigation

`frontend/src/features/staff/staffNavigation.ts` — exactly the verified
staff capabilities:

| Key | Label | Verified by |
|---|---|---|
| `dashboard` | Dashboard | `/auth/me` identity |
| `approvals` | Student Approvals | `require_roles("admin","staff")` approval endpoints |
| `assistant` | AI Assistant | `get_current_user` chat contracts |
| `profile` | Profile | `/auth/me` identity |

Fail-closed behaviour (pinned by `staffNavigation.test.ts`):

- `admin` → `[]`, `faculty` → `[]`, `student` → `[]`,
  `null`/unknown → `[]` (no staff navigation for any other role).
- No Student Management, Attendance Management, Results Management,
  Test Results Management, Notices Management, Document Management,
  User Management, Role Management, or Institution Management entries —
  all of those are admin-only (403) server-side.
- Navigation is UX-only; the backend remains the authorization boundary.

## 8. Capability Audit

Audit performed over `backend/app/core/security.py`, `backend/app/api/*`,
`backend/app/services/*`, `backend/app/repositories/*`, `backend/tests/*`,
`docs/locks/PHASE_6_4_LOCK.md`, `docs/locks/PHASE_6_6_LOCK.md`,
`frontend/src/*`.

`require_roles` occurrences involving staff:

- `require_roles("admin", "staff")` — Phase 6.4 student approval queue
  (`GET /admin/students/pending`, `POST /admin/students/{id}/approve`,
  `POST /admin/students/{id}/reject`) — the ONLY `/admin/*` surface
  authorized for staff.
- `require_roles("admin", "staff", "faculty")` — document ingestion
  pipeline (`/documents/*`).
- `require_roles("admin")` — every other `/admin/*` endpoint (students
  CRUD, attendance, results, test-results, notices, FAQs,
  knowledge-sources, documents, dashboard, `/me`, audit-logs).

Capability matrix (final; the implementation matches this exactly):

| Capability | Backend Contract | Staff Authorized | UI |
|---|---|---|---|
| Identity | `/auth/me` — verified | yes | yes (safe fields) |
| Dashboard | `/auth/me` (no async data) | yes | yes |
| Student Approvals | `require_roles("admin","staff")` — verified | yes (tenant-scoped) | yes (`StaffApprovals`) |
| Students (CRUD/list) | `require_roles("admin")` — verified | no (403) | no |
| Attendance | `require_roles("admin")`; `/students/me/*` 404 | no | no |
| Results | `require_roles("admin")`; `/students/me/*` 404 | no | no |
| Test Results | `require_roles("admin")`; `/students/me/*` 404 | no | no |
| Notices | `require_roles("admin")`; `/students/me/*` 404 | no | no |
| Resources (listing/management) | `require_roles("admin")` | no | no |
| Documents (listing/management) | `require_roles("admin")` | no | no |
| Document ingestion pipeline | `require_roles("admin","staff","faculty")` | yes, but no listing contract | no (see §16) |
| User/Role/Institution management | admin-only tenancy/authorization services | no | no |
| AI Assistant | `get_current_user` chat contracts — verified | yes | yes (existing `ChatShell`) |
| Profile | `/auth/me` — verified | yes | yes |

## 9. Dashboard

`StaffDashboard.tsx` renders ONLY information backed by an existing contract:

- **Identity** — from the server-authoritative `/auth/me` response held in
  `AuthProvider` state (never re-derived client-side).
- **Operational workspace** — the verified staff capability map
  (`STAFF_WORKSPACE_SURFACES`, a UI mirror of the §8 matrix), introduced by
  the neutral wording: "Staff workspace capabilities are available based on
  your assigned permissions." Unavailable surfaces render "Not available
  yet" with non-failure descriptions.
- **Entry points** — buttons to the verified Student Approvals view and the
  AI Assistant.

No fabricated data: no counts of students, attendance percentage, pending
approvals, results, notices, resources or assigned subjects are ever
rendered (pinned by DOM assertions in `StaffDashboard.test.tsx`).

## 10. Identity

`StaffIdentityCard.tsx` renders only safe `/auth/me` fields:

| Field | Handling |
|---|---|
| `email` | rendered ("Not provided" if absent) |
| `role` | rendered as the static word "Staff" |
| `institution_id` | presence only — "Linked to your institution" / "No institution linked"; the UUID is never rendered |
| `user_id` | internal — never rendered |
| `auth_user_id` | internal auth UUID — never rendered |

DOM assertions in `StaffDashboard.test.tsx` pin that none of the internal
identifiers and no token material ("bearer"/"token") appear in the rendered
output.

## 11. Student Access

**Verified boundary:** Staff has NO general student-data access.

- `GET /admin/students`, `GET/PATCH/DELETE /admin/students/{id}` →
  `require_roles("admin")` → 403 `FORBIDDEN`
  (pinned: `test_staff_denied_admin_student_list`, `_read`, `_update`,
  `_delete`).
- `/students/me/*` → the student-only identity chain
  (`get_student_context`) → 404 `STUDENT_PROFILE_NOT_FOUND` for a staff
  principal — a staff account has no `students` row
  (pinned: `test_staff_cannot_read_own_student_profile` and six sibling
  tests).

The ONE exception is the Phase 6.4 approval queue, which deliberately
exposes the minimal `STUDENT_APPROVAL_COLUMNS` projection to admin+staff
approvers. It is implemented as `StaffApprovals` (see §20 for scoping).
Student registration approval was verified as a legitimate staff contract;
student lookup/records/status management/suspension were verified as
admin-only and were NOT copied into Staff.

## 12. Attendance

- View: DENIED. `/admin/*attendance*` is `require_roles("admin")` (403);
  `/students/me/attendance*` is the student-only identity chain (404 for
  staff).
- Record/modify: DENIED (same 403 boundary).
- Pinned by `test_staff_denied_admin_attendance_create` and
  `test_staff_cannot_read_student_attendance[_summary]`.
- No attendance UI exists in the staff shell.

## 13. Results

- View: DENIED. `/admin/results*`, `/admin/students/{id}/results*` are
  `require_roles("admin")` → 403; `/students/me/results` → 404.
- Create/update/delete/CSV upload: DENIED (same 403 boundary).
- Pinned by `test_staff_denied_admin_results_create`,
  `test_staff_denied_admin_results_csv_upload`,
  `test_staff_denied_admin_student_results`,
  `test_staff_cannot_read_student_results`.
- No results UI exists in the staff shell.

## 14. Test Results

- View: DENIED. `/admin/test-results*`, `/admin/students/{id}/test-results`
  are `require_roles("admin")` → 403; `/students/me/test-results` → 404.
- Create/update/delete test scores: DENIED (same boundary).
- Pinned by `test_staff_denied_admin_test_results_create`,
  `test_staff_denied_admin_student_test_results`,
  `test_staff_cannot_read_student_test_results`.
- No test-results UI exists in the staff shell.

## 15. Notices

- View: DENIED. `/admin/notices` is `require_roles("admin")` → 403;
  `/students/me/notices` is the student-only chain → 404 for staff.
- Create/edit/delete/publish: DENIED (same 403 boundary).
- Pinned by `test_staff_denied_admin_notices_list`,
  `test_staff_denied_admin_notice_create`,
  `test_staff_cannot_read_student_notices`.
- No staff notice-management interface exists. Publication privileges were
  NOT granted based on the staff role.

## 16. Learning Resources

- Listing/management: DENIED. `/admin/knowledge-sources` is
  `require_roles("admin")` → 403
  (pinned: `test_staff_denied_admin_knowledge_sources`).
- Upload pipeline (`/documents/ingest|extract|chunk|embed`) IS
  staff-authorized (`require_roles("admin", "staff", "faculty")` with
  `assert_tenant_object` tenant checks — pinned:
  `test_staff_ingest_allowed_for_own_tenant`,
  `test_staff_ingest_denied_for_cross_tenant_knowledge_source`).
- **Following the Phase 6.17 precedent:** authorization to ingest does NOT
  imply a management surface. There is NO staff-facing knowledge-source
  listing contract to select an ingestion target, so NO upload UI is
  rendered. Documented as unavailable rather than inferred.

## 17. Documents

- Document listing/detail/versions/upload/delete:
  `/admin/documents*` is `require_roles("admin")` → 403.
- The ingestion pipeline authorization is the same situation as §16 —
  pipeline-authorized, management-unavailable. No staff document-management
  UI exists.

## 18. User Management

- Staff has NO backend contract for user management, role management, or
  institution management. The tenancy/authorization services
  (`backend/app/services/tenancy.py`, `authorization.py`) gate those
  operations on platform/institution-organization admin authority — a bare
  `staff` role receives 403.
- Staff also has NO contract for student account approval beyond the Phase
  6.4 queue (which is exactly what `StaffApprovals` implements), no account
  suspension, no staff lookup, no student-status editing (PATCH
  `/admin/students/{id}` is admin-only).
- Nothing was copied from the Admin `StudentManager` — the admin student
  CRUD is admin-only (403 for staff, pinned by four tests).

## 19. AI Assistant

- Reuses the existing `ChatShell` verbatim inside
  `<section aria-label="AI Assistant">`.
- Chat contracts are authorized for staff: conversations list and generation
  chat use the plain `get_current_user` dependency (verified for the staff
  principal by `test_staff_can_list_own_conversations`; the non-student
  chat path itself is covered by `tests/test_personalized_chat_6147.py`,
  including the `[staff]` parametrization).
- No conversations/chat UI/message rendering/retrieval/generation/model
  selection code was duplicated or redesigned.

## 20. Profile

- `StaffProfile.tsx` reuses `StaffIdentityCard` (safe `/auth/me` fields)
  plus an explicit, honest statement that the institution has not linked
  additional profile details.
- NOT invented: employee ID, department, designation, subject assignments,
  staff ID, phone number, personal details — none of these exist in any
  backend contract for staff.

## 21. Academic Context

Explicit audit result: Staff currently has **no** staff profile model, no
department model, no designation, no assigned classes, no assigned
subjects, no assigned students, no academic-year assignment, and no
semester assignment anywhere in the backend (`backend/app/models/*`,
`backend/app/repositories/*`, `backend/app/schemas/*`).

- No speculative academic model was created in Phase 6.18.
- The staff foundation remains minimal; when the institution later links
  academic context to staff accounts, it will appear in the profile view.

## 22. Tenant Isolation

Every staff operation involving institutional data is tenant-scoped
server-side; the frontend never filters, hides, or supplies tenant identity:

- **Approval queue** — a tenant-bound staff caller always receives their OWN
  institution's pending list. `_approval_scope` resolves the tenant from the
  authenticated JWT; a foreign `?institution_id=` is rejected with 403
  `TENANT_MISMATCH` and the staff client never sends one.
  (Pinned: `test_staff_lists_pending_students_for_own_tenant`,
  `test_staff_foreign_institution_filter_rejected_with_tenant_mismatch`.)
- **Approve/reject** — the service resolves the target student and enforces
  the tenant BEFORE any state change; a cross-tenant student produces 403
  `TENANT_MISMATCH` with no write
  (pinned: `test_staff_cannot_approve_cross_tenant_student`,
  `test_staff_cannot_reject_cross_tenant_student`).
- **Ingestion** — the knowledge-source tenant must match the staff caller's
  tenant (403 `TENANT_MISMATCH` otherwise).
- `/auth/me` returns the staff tenant resolved server-side.

```
Staff A / Institution A -> Institution A queue/approvals   ✓ allowed
Staff A / Institution A -> Institution B data              ✗ 403 TENANT_MISMATCH
```

## 23. Ownership Isolation

- Approval decisions accept NO request body fields, so `institution_id`,
  `role`, or `approval_status` tampering is inert by construction; the
  transition target is hardcoded server-side per endpoint.
- The staff client sends only the student's own row identifier in the URL
  path; query parameters such as `?institution_id=` or `?staff_id=` cannot
  widen scope (pinned:
  `test_staff_cannot_widen_approval_scope_with_identity_parameters` — the
  decision is still executed within the caller's OWN tenant).
- No Staff-owned resource exposes client-controllable identity parameters;
  authorization is derived server-side from the JWT context.

## 24. Privileged Route Protection

Staff is denied (403 `FORBIDDEN`) on every admin-only surface
(pinned by the `test_staff_denied_admin_*` suite):

| Endpoint | Guard | Staff result |
|---|---|---|
| `/admin/me` | `require_roles("admin")` | 403 |
| `/admin/dashboard` | `require_roles("admin")` | 403 |
| `/admin/students` (list/CRUD) | `require_roles("admin")` | 403 |
| `/admin/*attendance*` | `require_roles("admin")` | 403 |
| `/admin/results*` (+ CSV) | `require_roles("admin")` | 403 |
| `/admin/test-results*` | `require_roles("admin")` | 403 |
| `/admin/notices*` | `require_roles("admin")` | 403 |
| `/admin/faqs*` | `require_roles("admin")` | 403 |
| `/admin/knowledge-sources*`, `/admin/documents*` | `require_roles("admin")` | 403 |
| `/admin/audit-logs` | `require_roles("admin")` | 403 |
| `/students/me/*` | student identity chain | 404 |

The single deliberate exception is the Phase 6.4 approval boundary
(`require_roles("admin", "staff")`), which is pre-existing, locked policy
(`docs/locks/PHASE_6_6_LOCK.md` §"Permitted staff operations": student
approval/rejection within own institution; ingestion where existing policy
permits; cannot automatically inherit admin-only privileges). No admin
authorization rule was weakened to make the staff UI work.

## 25. Data Minimization

- The staff UI renders only data necessary for the verified workflow.
- The approval queue renders: student number, email, register number,
  university roll number, enrollment status, approval status. Internal
  identifiers (`student_id`, `user_id`, `institution_id`) present in the
  payload are never rendered (DOM-asserted in `StaffApprovals.test.tsx`).
- The queue payload itself is the pre-existing minimal Phase 6.4 projection
  (`STUDENT_APPROVAL_COLUMNS`) — pinned by
  `test_approval_queue_projection_never_contains_secret_material` to contain
  no credential/token/secret material.
- Never rendered anywhere in the staff shell: JWTs, access tokens, password
  data, auth secrets, internal UUIDs, database primary keys, hidden
  authorization metadata (DOM assertions in `StaffDashboard.test.tsx`).

## 26. Loading / Error Handling

- **Queue** — `loading` ("Loading pending registrations…"), `empty`
  ("No students are awaiting approval right now."), `error` (role="alert"
  + Retry button that recovers), per-decision error surfaced via an
  `aria-live="polite"` status region (never color-only).
- **Shell** — only rendered once `/auth/me` has loaded, so no fabricated
  mid-load state; a missing identity shows a controlled neutral state with
  sign-out.
- No fake fallback data anywhere. The dashboard is synchronous over
  AuthProvider state, so it has no async states to fake.

## 27. Request Efficiency

Initial staff dashboard requests: **0** (the dashboard renders entirely
from AuthProvider state + the static verified capability map).

| Request | When | Why required |
|---|---|---|
| `GET /auth/me` | login/restore (existing) | canonical identity + role; already in `AuthProvider` |
| `GET /admin/students/pending` | ONLY when the staff member opens Student Approvals | the queue is the one async staff dataset; not available in state |
| `POST .../approve` / `.../reject` | on explicit staff decision | mutations |
| `GET /conversations` | inside existing `ChatShell` | existing chat bootstrap (unchanged) |

- No duplicate calls for information already in `AuthProvider` (no
  `/admin/me` probe, no second identity request).
- The queue is loaded lazily — navigating to the dashboard or assistant
  never triggers it.
- Retries re-list the queue (a read); mutations are never auto-retried, so
  a retry cannot duplicate an approval decision (a second decision on the
  same row would 409 `STUDENT_NOT_PENDING` server-side anyway).

## 28. Session Lifecycle

Phase 6.15 behaviour is reused unchanged — no staff-specific session logic:

- **Login** — existing `AuthProvider.login` → `/auth/login` or
  `/auth/student/login` routing; `/auth/me` bootstrap.
- **Page refresh / restore** — saved token re-validated through `/auth/me`;
  the staff shell renders from the restored server-authoritative role.
- **Token expiry** — the shared API client's 401 handling calls
  `notifySessionExpired(accessToken)` (token-scoped, Phase 6.15.7); the
  staff queue request inherits this via the shared `requestJson` helper.
- **Logout** — `logout()` clears local state only (stateless JWT; no
  backend revocation endpoint exists).
- **Multi-tab** — the `storage`-event cross-tab consistency applies to the
  staff shell exactly as to every other shell.

## 29. Accessibility

- `<nav aria-label="Staff navigation">` landmarks; every view is reachable
  by keyboard (native `<button>` elements with visible
  `focus:ring-2 focus:ring-emerald-400` indicators).
- `aria-current="page"` on the active navigation item.
- Semantic headings: one `h1` per view (Dashboard / Student Approvals /
  Profile), `h2` sections with `aria-labelledby`.
- Semantic `<dl>` structures for identity and queue fields.
- Status messages use `role="status"` (loading/empty/action feedback),
  `role="alert"` (load error), and `aria-live="polite"` regions — status is
  never communicated by color alone.
- Approve/Reject buttons are disabled (with `disabled:opacity-60` AND text
  unchanged labels) while a decision is in flight.

## 30. Responsive Behavior

- The shell mirrors the Phase 6.17 responsive patterns: `min-w-0` +
  `break-words` on all text containers, `overflow-x-clip` on the page root
  (no page-level horizontal scrolling), `flex-wrap` header/navigation.
- Identity/profile grids collapse `sm:grid-cols-2`; workspace cards flow
  `sm:grid-cols-2 lg:grid-cols-3`; queue rows wrap with
  `flex-wrap`/`min-w-0` so action buttons never clip content on mobile.
- No tables are used in the staff UI (card/list layouts only), so there is
  no table overflow risk at any breakpoint.

## 31. Frontend Tests

Added (`frontend/src/features/staff/`):

| File | Coverage |
|---|---|
| `staffNavigation.test.ts` | staff navigation content; admin/faculty/student/null/unknown roles fail closed; no admin labels; verified/unavailable capability map pinned |
| `StaffShell.test.tsx` | shell renders for staff; nav content + `aria-current`; ChatShell reuse; approvals + profile navigation; no admin/student/faculty navigation; neutral missing-identity state; sign out |
| `StaffDashboard.test.tsx` | safe identity fields; internal-ID/token absence; verified workspace surfaces; no fabricated counts; entry-point navigation; profile honesty |
| `StaffApprovals.test.tsx` | loading/empty/error/retry states; safe-field rendering + internal-ID absence; approve + reject flows; 409 already-processed refresh; decision failure isolation |

`App.test.tsx` updated: `role = 'staff'` selects `StaffShell` (with
"Staff navigation"); admin/faculty/student selections unchanged;
unknown/null roles still fail safe.

## 32. Backend Tests

Added `backend/tests/test_staff_experience_phase_6_18.py` (43 tests):

1. **Role resolution** — `resolve_primary_role(["staff"]) == "staff"`;
   multi-role precedence unchanged (`admin > staff > faculty > student`);
   `/auth/me` returns `role: "staff"` + tenant; client-supplied
   role/institution parameters cannot override.
2. **Authorized staff access** — pending list scoped to own tenant (service
   called with the caller's tenant, no `institution_id` needed);
   own-institution filter accepted; approve/reject executed within the
   caller's tenant with audit logging.
3. **Unauthorized denial** — 14 admin surfaces pinned to 403 `FORBIDDEN`
   (`/admin/me`, dashboard, students list/read/update/delete, attendance,
   results create + CSV, student results, test-results create + read,
   notices list/create, FAQs, knowledge-sources, audit-logs); 9
   `/students/me/*` endpoints pinned to 404 `STUDENT_PROFILE_NOT_FOUND`.
4. **Tenant isolation** — foreign `?institution_id=` on the queue → 403
   `TENANT_MISMATCH` with no service call; cross-tenant approve/reject →
   403 `TENANT_MISMATCH` with no write.
5. **Cross-privilege escalation** — tenant-less (platform-level) staff →
   403 on all three approval endpoints (no silent authority).
6. **Client-controlled parameter neutralization** — identity parameters
   cannot widen the queue or a decision; the student chain ignores them.
7. **AI Assistant** — staff can list own conversations.
8. **Ingestion** — staff ingest allowed for own tenant; cross-tenant
   knowledge source → 403 `TENANT_MISMATCH`.
9. **Data minimization** — the approval projection contains no
   credential/token/secret material.

No existing test was modified, weakened, or skipped.

## 33. Full Regression

Executed at the end of the phase (Windows, repo root):

| Gate | Command | Result |
|---|---|---|
| Backend | `python -m pytest tests -q` | **1883 passed, 15 skipped, 0 failed** |
| Frontend tests | `npx vitest run` | **41 files, all passed (0 failed)** |
| TypeScript | `npx tsc -b` | **OK (exit 0, no errors)** |
| Production build | `npm run build` | **OK (`dist/` emitted)** |

All existing authentication, student, faculty, admin, RAG, and chat suites
remain green; no test was disabled or weakened.

## 34. Final Status & Limitations

**Implemented capabilities (verified backend contracts):**

| Requirement | Status |
|---|---|
| Staff role resolution via `/auth/me` | ✓ (precedence pinned; no `/admin/me`) |
| StaffShell implemented | ✓ (`StaffShell.tsx`, wired in `App.tsx`) |
| Staff navigation fails closed | ✓ (staff-only; all other roles → `[]`) |
| Staff dashboard implemented | ✓ (zero fabricated data) |
| Staff identity safely rendered | ✓ (no internal IDs / tokens) |
| Student approval queue workspace | ✓ (`StaffApprovals` — the verified Phase 6.4 staff contract) |
| Existing ChatShell reused | ✓ |
| Student access audited | ✓ (admin-only except approval queue; pinned) |
| Attendance access audited | ✓ (denied; documented) |
| Results / Test-results access audited | ✓ (denied; documented) |
| Notice access audited | ✓ (denied; documented) |
| Learning-resource / document access audited | ✓ (pipeline authorized; no listing contract → no UI) |
| User-management access audited | ✓ (admin-only; nothing copied) |
| Tenant isolation verified | ✓ (403 `TENANT_MISMATCH` pinned) |
| Ownership boundaries verified | ✓ (no client-controlled identity params) |
| Admin-only routes protected | ✓ (14 surfaces pinned to 403) |
| Session lifecycle reused | ✓ (Phase 6.15 unchanged) |
| Accessibility verified | ✓ (landmarks, focus, aria-current, status roles) |
| Responsive behaviour verified | ✓ (Phase 6.17 patterns reused) |
| Frontend tests pass | ✓ (32 new staff tests; 41 files green) |
| Backend tests pass | ✓ (43 new staff tests; 1883 passed) |
| TypeScript / production build pass | ✓ |
| Documentation contains exactly 34 sections | ✓ (this document) |
| Git scope contains no unrelated changes / no commit | ✓ (see below) |

**Unavailable capabilities (documented, NOT implemented — no staff backend
contract):** student records management, attendance, results, test results,
notices, FAQs, learning-resource and document listing/management, user /
role / institution management, document upload UI (no knowledge-source
listing contract), staff profile/academic context (no staff profile model
exists in the backend).

**Intentionally deferred:** everything requiring a new backend contract.
Phase 6.18 introduced no endpoint, no role, no permission, and no data
model.

**Git scope (files changed/added by Phase 6.18):**

- Added: `backend/tests/test_staff_experience_phase_6_18.py`
- Added: `frontend/src/features/staff/StaffShell.tsx`,
  `StaffDashboard.tsx`, `StaffIdentityCard.tsx`, `StaffProfile.tsx`,
  `StaffApprovals.tsx`, `staffNavigation.ts`,
  `staffNavigation.test.ts`, `StaffShell.test.tsx`,
  `StaffDashboard.test.tsx`, `StaffApprovals.test.tsx`
- Modified: `frontend/src/App.tsx` (staff shell selection + import),
  `frontend/src/App.test.tsx` (staff expectation),
  `frontend/src/services/adminApi.ts` (three approval-queue client
  functions reusing the shared `requestJson` contract),
  `frontend/src/types/admin.ts` (`PendingStudent` type mirroring the
  backend `STUDENT_APPROVAL_COLUMNS` projection)
- Added: `PHASE_6_18_STAFF_EXPERIENCE_FOUNDATION.md` (this document)

No backend production file was modified. No commit was created.

**STOP** — Phase 6.18 ends here. Phase 6.19 was not started and no commit
was created.






