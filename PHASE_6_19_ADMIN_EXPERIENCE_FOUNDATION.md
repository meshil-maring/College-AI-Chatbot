# Phase 6.19 — Admin Experience & Administrative Workspace Foundation

## 1. Phase Identity

- **Phase:** 6.19
- **Name:** Admin Experience & Administrative Workspace Foundation
- **Status:** Implemented & verified
- **Previous phase:** 6.18 — Staff Experience & Operational Workspace Foundation
- **Primary objective:** Consolidate the authenticated Admin experience into a
  server-authoritative, production-safe administrative workspace by exposing
  only existing backend contracts, fixing verified frontend defects, and
  pinning the whole contract with regression coverage.

Phase 6.19 is a **hardening and consolidation** phase. It adds **no** backend
endpoint, role, permission, or database object. Every admin surface it renders
already existed and was already authorized server-side by
`require_roles("admin", ...)`, with the single pre-existing Phase 6.4 staff
approval exception. The phase makes the administrative workspace honest,
testable, and drift-proof.

## 2. Objective

- Keep the admin role **server-authoritative** (`/auth/me` → `user.role`); the
  frontend never decides who is an admin.
- Give the admin shell **one** navigation definition with fail-closed
  behaviour for every non-admin role.
- Expose **only** capabilities that map to a verified, already-authorized
  backend contract; document the rest as unavailable instead of inventing UI.
- Fix the **verified frontend defects** found during the audit (wrong CSV
  route and response shape; client-controlled / hardcoded tenant parameters).
- Remove client-controlled identity and tenant parameters from admin screens.
- Preserve tenant isolation, role boundaries, and data minimization.
- Add regression coverage on both sides so the contract cannot silently drift.
- Leave backend production behaviour **unchanged**.

## 3. Scope

Worked on:

- Admin role-resolution audit and a full admin **capability matrix** over
  `backend/app/api/admin.py`, `backend/app/core/security.py`, and the
  `frontend/src/features/admin/*` surfaces.
- `adminNavigation.ts` — a single navigation model (11 real-contract items,
  fail-closed for every non-admin role).
- `AdminShell.tsx` — rewritten to consume the navigation model, add the
  Approvals / AI Assistant / Profile views, emit one `h1` per view and
  `aria-current`, and render **no** `<nav>` when navigation is empty.
- New `AdminIdentityCard.tsx` + `AdminProfile.tsx` — safe `/auth/me` fields
  only.
- New `AdminApprovals.tsx` — reuses the Phase 6.4 approval contract
  (`require_roles("admin","staff")`).
- `StudentManager.tsx` / `DocumentManager.tsx` — tenant derived from
  `user.institution_id`; the manual UUID input and the hardcoded
  `DEMO_INSTITUTION_ID` were removed.
- `ResultsManager.tsx` / `adminApi.ts` — CSV upload corrected to
  `POST /admin/results/csv-upload` with the required `institution_id` Form
  field and the real `CsvUploadResult` response shape.
- `types/admin.ts` — added `CsvRowError` / `CsvUploadResult`.
- New frontend tests: `adminNavigation.test.ts`, `AdminDashboard.test.tsx`,
  `AdminApprovals.test.tsx`, `ResultsManager.test.tsx`, rewritten
  `AdminShell.test.tsx`.
- New backend suite `test_admin_experience_phase_6_19.py`.
- Full regression and this document.

Explicitly NOT implemented (no such contract, or out of scope):

- Any new backend endpoint, role, permission, or migration.
- User / role / institution management UIs.
- A router library (none is installed — the shell uses local view state).
- Admin-specific academic data models (no employee ID, designation,
  department, or contact model exists for admin accounts).
- Mobile application; redesign of the student / faculty / staff shells.

## 4. Architecture Baseline

The following contracts were treated as frozen and are unchanged:

```
Authentication
    Supabase Auth -> JWT -> get_current_user -> public.users
                -> user_roles -> roles -> resolve_primary_role
                -> /auth/me -> AuthProvider -> AdminShell

Tenant resolution
    authenticated user -> institution resolution -> tenant-scoped admin data

Roles (unchanged): admin | staff | faculty | student
```

Note: the admin workspace resolves its tenant from the identity already
present in `AuthProvider` state (populated by the `/auth/me` bootstrap). It
does **not** probe `GET /admin/me` for role or identity: one authenticated
request bootstraps the whole workspace. Authorization is still fully
backend-enforced, because every admin API call carries the bearer token and
`/admin/*` re-resolves the caller's roles server-side from the JWT.

Key primitives reused verbatim (no modification):

| Primitive | File | Reuse |
|---|---|---|
| `get_current_user` | `backend/app/core/security.py` | identity always server-side |
| `require_roles(*allowed)` | `backend/app/core/security.py` | 401/403 on every privileged route |
| `resolve_primary_role` | `backend/app/core/security.py` | canonical role for `/auth/me` |
| `scope_tenant` / `assert_tenant_object` | `backend/app/core/security.py` | 403 `TENANT_MISMATCH` isolation |
| `_approval_scope` | `backend/app/api/admin.py` | tenant-pinned Phase 6.4 approval queue |
| `requestJson` / `notifySessionExpired` | `frontend/src/services/*` | shared transport + 401 session handling |
| `AuthProvider` | `frontend/src/features/auth/AuthProvider.tsx` | canonical identity/role/tenant state |
| `ChatShell` | `frontend/src/features/chat/ChatShell.tsx` | existing authenticated chat surface |

## 5. Role Resolution

The admin role is resolved **exclusively server-side** and reaches the client
through the canonical `/auth/me` bootstrap:

- `SUPPORTED_ROLES` and `resolve_primary_role` (`backend/app/core/security.py`)
  compute the canonical role with fixed precedence:
  **admin > staff > faculty > student**.
- `GET /api/v1/auth/me` returns the authenticated identity: `email`, `role`
  (canonical), `institution_id`, `user_id`, `auth_user_id`.
- `AuthProvider` stores that response; `App.tsx` renders `AdminShell` only when
  the resolved role is `admin`.

Pinned guarantees (backend, `test_admin_experience_phase_6_19.py`):

| Test | Guarantee |
|---|---|
| `test_resolve_primary_role_admin_precedence_unchanged` | precedence untouched (`["student","admin"]` → `admin`) |
| `test_auth_me_returns_admin_role_with_tenant` | `/auth/me` returns `admin` + tenant |
| `test_auth_me_client_params_cannot_override_admin_role` | client-supplied params cannot change the resolved role |

Two independent fail-closed gates exist on the frontend:

1. **Shell selection** (`App.tsx`) — non-admins never receive `AdminShell`.
2. **Navigation model** (`buildAdminNavigation`) — returns `[]` for `null`,
   unknown, `staff`, `faculty`, and `student`, so even if the shell were
   rendered it would expose no admin surface.

Neither gate is a security boundary. A user who manually requests an admin URL
still receives `403 FORBIDDEN` unless the server resolves the `admin` role for
their account.

## 6. AdminShell

`frontend/src/features/admin/AdminShell.tsx` (rewritten in Phase 6.19):

- Navigation, headings, and fail-closed gating are imported from
  `adminNavigation.ts` — the shell no longer inlines its own link list.
- Views rendered: `dashboard`, `approvals`, `students`, `attendance`,
  `results`, `test-results`, `notices`, `documents`, `faqs`, `assistant`,
  `profile` (local `useState<AdminView>`, default `dashboard`).
- The header renders `<nav aria-label="Admin navigation">` **only when the
  navigation is non-empty** (`navigation.length > 0`); otherwise no `<nav>`
  landmark is emitted at all.
- The active item carries `aria-current="page"`.
- Exactly one `h1` per view, taken from `ADMIN_VIEW_HEADINGS`. The `assistant`
  view intentionally omits the shell `h1` because the embedded `ChatShell`
  owns its own heading structure (avoiding a duplicate `h1`).
- `approvals` requires a non-null `accessToken`; if the session cannot be
  verified it shows a controlled `role="status"` message instead of calling
  the API.
- When `user === null`, the shell renders a single `role="status"` panel
  ("Admin workspace unavailable") with a sign-out button — never a fabricated
  or partially populated admin UI.
- The shell does **not** probe `GET /admin/me`: identity and role come from
  `AuthProvider`, so exactly one authenticated request bootstraps the
  workspace.
- Session expiry is inherited, never duplicated: every request goes through the
  shared API client (`requestJson` → 401 → `notifySessionExpired` →
  `AuthProvider`).

## 7. Navigation

`frontend/src/features/admin/adminNavigation.ts` defines the single admin
navigation, in display order. Every entry maps to a server-verified contract:

| Key | Label | Backend contract | Guard |
|---|---|---|---|
| `dashboard` | Dashboard | `GET /admin/dashboard` | `require_roles("admin")` |
| `approvals` | Student Approvals | `GET /admin/students/pending`, `POST /admin/students/{id}/approve\|reject` | `require_roles("admin","staff")` + `_approval_scope` |
| `students` | Students | `GET /admin/students` (+ CRUD) | `require_roles("admin")` |
| `attendance` | Attendance | `GET/POST/PATCH/DELETE /admin/attendance*` | `require_roles("admin")` |
| `results` | Results | `GET/POST/PATCH/DELETE /admin/results*`, `POST /admin/results/csv-upload` | `require_roles("admin")` |
| `test-results` | Test Results | `GET/POST/PATCH/DELETE /admin/test-results*` | `require_roles("admin")` |
| `notices` | Notices | CRUD `/admin/notices*` | `require_roles("admin")` |
| `documents` | Documents | CRUD `/admin/knowledge-sources*`, `/admin/documents*` (+ `/documents` pipeline) | `require_roles("admin")` |
| `faqs` | FAQs | CRUD `/admin/faqs*` | `require_roles("admin")` |
| `assistant` | AI Assistant | `GET /conversations`, `POST /generation/chat` | `get_current_user` |
| `profile` | Profile | `/auth/me` identity already in `AuthProvider` state | `get_current_user` |

Fail-closed behaviour (pinned by `adminNavigation.test.ts`):

- `buildAdminNavigation('admin')` → all 11 items.
- `staff`, `faculty`, `student`, `null`, and any unknown string → `[]`.
- `ADMIN_VIEW_HEADINGS` has a heading for **every** `AdminView` (exhaustive
  `Record<AdminView, string>`, so a new view cannot compile without a heading).
- No speculative entries (no user management, no role management, no
  institution administration) — those endpoints exist server-side for admins
  but have no frontend manager today, so no navigation entry is added.

Navigation is UX-only. Removing or editing this file cannot grant access to
anything.

## 8. Capability Matrix

Audit performed over `backend/app/api/admin.py`, `backend/app/api/*`,
`backend/app/core/security.py`, `backend/app/services/*`, and
`frontend/src/features/admin/*`.

`require_roles` occurrences (unchanged by this phase):

- `require_roles("admin")` — every admin-only surface: dashboard, `/me`,
  student CRUD/list, attendance, results (+ CSV upload), test-results, notices,
  FAQs, knowledge-sources, documents, and audit logs.
- `require_roles("admin", "staff")` — **only** the Phase 6.4 student approval
  queue (`GET /admin/students/pending`, `POST /admin/students/{id}/approve`,
  `POST /admin/students/{id}/reject`).
- `require_roles("admin", "staff", "faculty")` — the document ingestion
  pipeline (`/documents/*`).

Capability matrix (final; the implementation matches this exactly):

| Capability | Backend Contract | Admin Authorized | UI |
|---|---|---|---|
| Identity | `/auth/me` — verified | yes | yes (safe fields) |
| Dashboard | `GET /admin/dashboard` — verified | yes (tenant-scoped) | yes (`AdminDashboard`) |
| Student Approvals | `require_roles("admin","staff")` — verified | yes (tenant-scoped) | yes (`AdminApprovals`) |
| Students (list/CRUD) | `require_roles("admin")` — verified | yes (tenant-scoped) | yes (`StudentManager`) |
| Attendance | `require_roles("admin")` — verified | yes | yes (`AttendanceManager`) |
| Results | `require_roles("admin")` — verified | yes | yes (`ResultsManager`) |
| Results CSV upload | `POST /admin/results/csv-upload` — verified | yes (tenant-scoped) | yes (`ResultsManager`) |
| Test Results | `require_roles("admin")` — verified | yes | yes (`TestResultsManager`) |
| Notices | `require_roles("admin")` — verified | yes | yes (`NoticeManager`) |
| FAQs | `require_roles("admin")` — verified | yes | yes (`FaqManager`) |
| Knowledge sources / Documents | `require_roles("admin")` — verified | yes | yes (`DocumentManager`) |
| Document ingestion pipeline | `require_roles("admin","staff","faculty")` | yes | via `DocumentManager` |
| AI Assistant | `get_current_user` chat contracts — verified | yes | yes (`ChatShell`) |
| Profile | `/auth/me` — verified | yes | yes (`AdminProfile`) |
| User / Role / Institution management | admin-authorization services | yes (backend) | **no UI** (not navigable) |
| Audit logs | `require_roles("admin")` | yes (backend) | surfaced read-only on the dashboard |

## 9. Dashboard

`AdminDashboard.tsx` renders real aggregated data from
`GET /api/v1/admin/dashboard`:

- **Counts** — Knowledge Sources, Documents, FAQs, Notices, Students, Results,
  Test Results, Attendance Records. Rendered as a `2`-column grid on small
  screens and `4`-column from `sm` up.
- **Recent Activity** — the contract's `recent_audit` entries (`action` +
  `performed_at`); when empty, the explicit neutral state "No recent activity."
- **Loading** — a `role="status"` region ("Loading dashboard…").
- **Error** — a `role="alert"` region plus a **Retry** button that re-issues
  the request and recovers.
- No fake fallback data; `summary === null` renders nothing rather than an
  invented dashboard.

The dashboard reads nothing from AuthProvider other than the access token, so
its data is always the server's view of the caller's own tenant.

## 10. Request Efficiency

| View | Requests on open | Notes |
|---|---|---|
| Shell (any view) | 0 extra | identity/role/tenant already in `AuthProvider` |
| Dashboard | 1 — `GET /admin/dashboard` | the only eager admin request |
| Approvals | 1 — `GET /admin/students/pending` | lazily loaded on view open |
| Students | 1 — `GET /admin/students` | lazily loaded |
| Results | 1 — `GET /admin/results` | lazily loaded |
| Profile | 0 | renders `AuthProvider` state |

- Exactly one `GET /admin/dashboard` per load is asserted by
  `AdminDashboard.test.tsx` ("requests the summary exactly once per load"),
  including on retry (a retry issues a second request only because the user
  asked for one).
- No duplicate identity calls: no `/admin/me` probe, no second `/auth/me`.
- Mutations are never auto-retried, so a retry cannot duplicate a write.
- Approvals discards stale results: `AdminApprovals` keeps a
  `requestGeneration` ref and ignores any response whose generation is no
  longer current, so a slow first load cannot overwrite a newer one.

## 11. Student Management

`StudentManager.tsx` (Phase 6.19 hardening):

- **Removed:** the manual "Enter institution UUID" text input — a
  client-controlled tenant parameter. Authorization always derives from the
  authenticated JWT server-side; `?institution_id=` remains only a
  server-validated filter.
- Tenant is now `user?.institution_id ?? null`, read exclusively from the
  server-authoritative identity in `AuthProvider` state (`/auth/me`).
- When no institution is linked (platform-level account), a controlled neutral
  state is rendered (`role="status"`: "No institution is linked to your
  administrator account…") instead of an error or a fabricated list.
- The list shows only Number, Status, Enrolled; internal identifiers are not
  rendered.
- Loading and error states use `role="status"` and `role="alert"`
  respectively.

## 12. Approval Workflow

`AdminApprovals.tsx` is the admin view of the **same** Phase 6.4 approval
contract (`require_roles("admin","staff")` with the tenant-pinned
`_approval_scope`):

```
GET  /api/v1/admin/students/pending
POST /api/v1/admin/students/{id}/approve
POST /api/v1/admin/students/{id}/reject
```

Server-side guarantees the UI relies on (never re-implemented client-side):

- the queue is scoped to the caller's **own** institution by the backend
  (`_approval_scope`); the client never sends an `institution_id`;
- the approve/reject bodies accept **no** fields, so no decision target can be
  spoofed from the client;
- every decision is audit-logged server-side.

UI behaviour:

- State machine: `{phase:'loading'} | {phase:'ready',students} |
  {phase:'error',message}`.
- **Stale-result protection** — a `requestGeneration` ref discards any
  response that is no longer the newest request.
- **409 `STUDENT_NOT_PENDING`** (another approver already decided) triggers a
  queue **refresh** instead of a fake success.
- **Duplicate-submission protection** — `busyStudentId` disables both Approve
  and Reject for all rows while a decision is in flight.
- Per-view status messaging; errors are never color-only.

Data minimization: each row renders only `student_number`, `email`,
`register_number`, `university_roll_number`, `status`, and `approval_status`
(missing values render `—`). Internal identifiers `student_id`, `user_id`, and
`institution_id` are present in the payload but are **never** rendered — this
is DOM-asserted in `AdminApprovals.test.tsx`.

## 13. Attendance

`AttendanceManager.tsx` is unchanged by Phase 6.19. It shows attendance records
for a selected student via `GET /admin/attendance*` (`require_roles("admin")`,
tenant-scoped server-side). The `student_id` typed into the lookup box is a
**query target**, never an authorization input: the backend re-scopes every
row to the admin's own tenant, so a foreign student returns 403/404 rather
than another institution's data. No client-side filtering is relied upon.

## 14. Results

`ResultsManager.tsx` + `adminApi.ts` — the phase's most important **verified
defect fix**:

| Aspect | Before (defective) | After (verified) |
|---|---|---|
| CSV route | `POST /admin/results/csv` | `POST /admin/results/csv-upload` |
| Request body | file only | multipart with required `institution_id` **and** `file` |
| Response shape | `{uploaded, errors}` | `{total_rows, inserted_count, failed_count, row_errors}` |
| Tenant | not sourced from identity | `user.institution_id` from `AuthProvider` |

- The `institution_id` field is a **server-validated filter**, not an
  authorization input: the endpoint re-scopes it via `scope_tenant`, so a
  foreign value is rejected with `403 TENANT_MISMATCH`.
- `types/admin.ts` gained `CsvRowError` / `CsvUploadResult` as an exact mirror
  of the backend service contract in
  `backend/app/services/admin_academics.py`.
- The upload control is disabled with a neutral status when the account has no
  institution linked, instead of guessing a tenant.
- `frontend/src/services/adminApi.test.ts` pins the corrected path
  (`expect(url).toBe('/api/v1/admin/results/csv-upload')`) and the `FormData`
  body, so the regression cannot silently return.
- Row-level errors are surfaced from `row_errors`; a partial upload still
  reports `inserted_count` / `failed_count` honestly.

Pinned backend tests: `test_admin_csv_upload_foreign_institution_rejected`,
`test_admin_csv_upload_own_institution_scopes_correctly`.

## 15. Notices

`NoticeManager.tsx` is unchanged by Phase 6.19: CRUD over `/admin/notices*`
plus publish/unpublish and pin/unpin, `require_roles("admin")`, tenant-scoped
server-side, using the shared admin API client. No client-supplied tenant
parameter is trusted.

## 16. Learning Resources

There is **no** admin "learning resources" surface, and none was invented.
The student-facing learning-resource contract is `GET /students/me/resources`
(student identity chain). Administration of the same content happens through
two admin-only surfaces that do exist:

- **Knowledge sources + documents** — `DocumentManager` (see §17).
- **FAQs** — `FaqManager` (`CRUD /admin/faqs*` with publish/unpublish).

Both are admin-only (`require_roles("admin")`) and are the authoritative,
verified way administrators curate what powers retrieval and RAG sync.

## 17. Documents

`DocumentManager.tsx` (Phase 6.19 hardening):

- **Removed:** the hardcoded `DEMO_INSTITUTION_ID` constant — a fabricated
  tenant. The tenant is now `user?.institution_id ?? null`, derived
  exclusively from the server-authoritative identity in `AuthProvider` state.
- `?institution_id=` is passed only to `GET /admin/knowledge-sources`, where it
  remains a **server-validated filter** (via `scope_tenant`), never an
  authorization input.
- On load the first knowledge source is auto-selected so the upload control is
  immediately usable (previously it stayed disabled on an empty ID).
- Upload / new-version / delete all go through `require_roles("admin")`
  endpoints; the ingestion pipeline is `require_roles("admin","staff",
  "faculty")`.
- When no institution is linked, a controlled neutral state is shown and
  knowledge-source creation is disabled instead of silently targeting a
  guessed tenant.

## 18. FAQ

`FaqManager.tsx` (pre-existing, unchanged) provides CRUD over `/admin/faqs*`
with publish/unpublish, using the shared admin API client. It requires the
`admin` role and is tenant-scoped server-side (`_assert_row_tenant` on
single-row operations). Its behaviour is covered by the pre-existing
`FaqManager.test.tsx`, which remains green.

## 19. AI Assistant

The `assistant` view reuses the existing `ChatShell`
(`frontend/src/features/chat/ChatShell.tsx`) — no new chat code:

- Authenticated chat contracts (`GET /conversations`,
  `POST /generation/chat`) are `get_current_user`-authorized, so an admin is
  allowed without any new permission.
- The shell wraps it in `<section aria-label="AI Assistant">`.
- The shell omits its own `h1` for this view so the embedded chat's heading
  structure is not duplicated (a single-`h1`-per-page rule).

## 20. Profile

`AdminProfile.tsx` + `AdminIdentityCard.tsx` render the safe identity the
backend actually returns from `/auth/me`, held in `AuthProvider` state:

| Field | Rendered as | Note |
|---|---|---|
| `email` | Email (or "Not provided") | safe |
| `role` | "Admin" | server-resolved, not client input |
| `institution_id` | **presence only** → "Linked to your institution" / "No institution linked" | the UUID itself is never displayed |

Explicitly **never** rendered: `user_id`, `auth_user_id`, any JWT / access
token / password material, and invented profile fields (employee ID,
designation, department, phone number) — none of those models exist for admin
accounts. `AdminProfile` states this limitation honestly rather than
fabricating data.

## 21. Tenant Isolation

Tenant isolation is enforced **server-side**; the frontend only supplies a
validated filter:

| Concern | Server mechanism | Client contribution |
|---|---|---|
| Every `/admin/*` request | `require_roles("admin")` + token identity | none (bearer token only) |
| List/read queries | `scope_tenant` / `user_tenant_id` | optional `?institution_id=` filter, validated |
| Single-row read/write | `_assert_row_tenant` → `403 TENANT_MISMATCH` | none |
| Approval queue | `_approval_scope` (tenant-pinned) | none — no `institution_id` sent |
| CSV upload | `scope_tenant` on the `institution_id` Form field | the field, re-validated |
| Dashboards | counts scoped to caller's tenant | none |

The client's tenant value now comes from exactly one place —
`user.institution_id` in `AuthProvider` state (`/auth/me`). The two
client-controlled tenant inputs that previously existed were removed:

1. the manual "Enter institution UUID" box in `StudentManager`;
2. the hardcoded `DEMO_INSTITUTION_ID` in `DocumentManager`.

Even if a caller forged `institution_id`, the backend would reject the
mismatch — so these removals improve correctness without weakening anything.

## 22. Cross-Tenant Regression Tests

Pinned in `backend/tests/test_admin_experience_phase_6_19.py`:

| Test | Guarantee |
|---|---|
| `test_admin_dashboard_scoped_to_own_tenant` | dashboard counts never leak another tenant |
| `test_admin_list_students_scoped_to_own_tenant` | student list scoped to caller's tenant |
| `test_admin_lists_pending_students_scoped_to_own_tenant` | approval queue tenant-pinned |
| `test_admin_foreign_institution_filter_rejected` | foreign `?institution_id=` → rejected |
| `test_admin_approves_pending_student_within_own_tenant` | in-tenant approval succeeds |
| `test_admin_cannot_approve_cross_tenant_student` | cross-tenant approve blocked |
| `test_admin_cannot_reject_cross_tenant_student` | cross-tenant reject blocked |
| `test_admin_cannot_read_cross_tenant_student` | cross-tenant read blocked |
| `test_admin_csv_upload_foreign_institution_rejected` | foreign CSV tenant → `TENANT_MISMATCH` |
| `test_admin_csv_upload_own_institution_scopes_correctly` | own-tenant CSV insert works |

## 23. Privileged Route Protection

Every privileged admin route is guarded server-side; the frontend is not a
security boundary.

| Endpoint | Guard | Non-admin result |
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
| `/admin/students/pending`, `.../approve`, `.../reject` | `require_roles("admin","staff")` | student/faculty → 403; staff allowed (tenant-pinned) |
| No token at all | `get_current_user` | 401 |

The **single deliberate exception** is the Phase 6.4 approval boundary, which
is pre-existing, locked policy (`docs/locks/PHASE_6_6_LOCK.md`). No admin
authorization rule was weakened to make the UI work; the phase only *exposed*
it in the admin shell. Pinned by
`test_student_denied_admin_surfaces`, `test_faculty_denied_admin_surfaces`,
`test_staff_denied_admin_surfaces_except_approval_queue`, and
`test_staff_approval_exception_remains_intact`.

## 24. Client-Controlled Identity Parameters

No client-supplied value can select an identity, role, or tenant-of-effect.

| Parameter | Where it appears | Why it is safe |
|---|---|---|
| `institution_id` (query) | `GET /admin/students`, `/admin/knowledge-sources` | re-scoped by `scope_tenant`; foreign value → `403 TENANT_MISMATCH` |
| `institution_id` (Form field) | `POST /admin/results/csv-upload` | re-scoped by `scope_tenant` |
| `student_id` (path/query) | attendance, results, test-results, approvals | re-scoped by `_assert_row_tenant`; foreign → `403`/`404` |
| role / claims in body | none | `/auth/me` ignores client role input |
| approve/reject body | none | the contract accepts **no** body fields |

Removed in this phase (previously client-controlled):

- `StudentManager`: the manual institution-UUID text input.
- `DocumentManager`: the hardcoded `DEMO_INSTITUTION_ID`.

Pinned backend tests:

- `test_auth_me_client_params_cannot_override_admin_role` — a client attempt to
  influence the resolved role is ignored.
- `test_admin_approval_identity_params_are_inert` — identity parameters sent to
  the approval endpoints have no effect.
- `test_admin_foreign_institution_filter_rejected` — a foreign filter is
  rejected rather than silently applied.

## 25. Data Minimization

- The admin UI renders only the data needed for each workflow.
- Approval rows render: student number, email, register number, university roll
  number, enrollment status, approval status. Internal identifiers
  (`student_id`, `user_id`, `institution_id`) in the payload are **never**
  rendered (DOM-asserted in `AdminApprovals.test.tsx`).
- `AdminIdentityCard` renders `email`, `role` ("Admin"), and institution
  **presence** only.
- Never rendered anywhere in the admin shell: JWTs, access tokens, password
  data, auth secrets, internal UUIDs, database primary keys, or hidden
  authorization metadata.
- Pinned by `test_admin_responses_expose_no_token_material`, which asserts that
  admin identity responses contain no credential/token/secret material.

## 26. Loading / Error / Retry

| Surface | Loading | Empty | Error / Retry |
|---|---|---|---|
| Dashboard | `role="status"` "Loading dashboard…" | "No recent activity." | `role="alert"` + **Retry** (recovers) |
| Approvals | `role="status"` loading state | "No pending registrations" style empty state | `role="alert"` + Retry; per-decision error via status message; 409 → refresh |
| Students | `role="status"` "Loading students…" | "No students found for your institution." | `role="alert"`; no-institution → neutral `role="status"` |
| Documents | `role="status"` | neutral source list | `role="alert"`; no-institution → neutral status + disabled upload |
| Results | `role="status"` | — | `role="alert"`; upload result reported from `row_errors` |
| Shell | — | — | `user === null` → `role="status"` "Admin workspace unavailable" + Sign out |

- No fake fallback data anywhere: reads that have not resolved render nothing or
  a neutral state, never an invented list.
- Retries re-issue **reads**; mutations are never auto-retried, so a retry
  cannot duplicate a write (a second decision on the same row would return
  `409 STUDENT_NOT_PENDING` server-side anyway).
- Status is never communicated by color alone.

## 27. Accessibility

- `<nav aria-label="Admin navigation">` landmark, rendered only when the
  navigation is non-empty.
- `aria-current="page"` on the active navigation item.
- Exactly one `h1` per view (from `ADMIN_VIEW_HEADINGS`); `h2`/`h3` section
  headings; sections use `aria-labelledby` where applicable.
- Semantic `<dl>` structures for identity and approval fields.
- Status regions use `role="status"` (loading/empty/action feedback) and
  `role="alert"` (load errors) — never color alone.
- Every interactive control is a native `<button>` with a visible
  `focus:ring-2 focus:ring-emerald-400` focus indicator, reachable by keyboard.
- Approve/Reject buttons are `disabled` **and** reduced-opacity
  (`disabled:opacity-60`) while a decision is in flight, so the busy state is
  not conveyed by color only.

## 28. Responsive Behavior

- The header and navigation use `flex-wrap` with `min-w-0` / `break-words` on
  text containers so long emails and labels never force horizontal page scroll.
- The shell root is `min-h-screen` with `min-w-0 max-w-7xl` content, matching
  the Phase 6.17/6.18 shells.
- Grid collapse: dashboard counts `grid-cols-2 sm:grid-cols-4`; profile/queue
  field grids `sm:grid-cols-2`.
- Tables (`StudentManager`, `AttendanceManager`) are wrapped in
  `overflow-x-auto` so they scroll locally instead of breaking the page layout.
- Approval rows wrap with `flex-wrap` / `min-w-0` so action buttons never clip
  content on narrow viewports.

## 29. Session Lifecycle

Phase 6.15 behaviour is reused unchanged — there is no admin-specific session
logic:

- **Login** — existing `AuthProvider.login` → `/auth/login` (or
  `/auth/student/login` routing); then the `/auth/me` bootstrap resolves the
  canonical role and tenant.
- **Page refresh / restore** — the saved token is re-validated through
  `/auth/me`; `AdminShell` renders from the restored server-authoritative role.
- **Token expiry** — the shared API client's 401 handling calls
  `notifySessionExpired(accessToken)` (token-scoped, Phase 6.15.7); every admin
  request inherits this through the shared `requestJson` helper.
- **Logout** — `logout()` clears local state only (stateless JWT; no backend
  revocation endpoint exists). Used by the header button and the
  identity-unavailable panel.
- **Multi-tab** — the `storage`-event cross-tab consistency applies to the admin
  shell exactly as to every other shell.

## 30. Frontend Tests

Added / rewritten (`frontend/src/features/admin/` and
`frontend/src/services/adminApi.test.ts`):

| File | Tests | Coverage |
|---|---|---|
| `adminNavigation.test.ts` | 4 | admin nav content; every other role + `null` + unknown fail closed; no invented/unauthorized entries; a heading for every view |
| `AdminShell.test.tsx` (rewritten) | 7 | canonical identity from auth state; never probes `GET /admin/me`; fail-closed navigation; no nav for non-admin roles; `aria-current`; profile view shows only safe fields; shared logout |
| `AdminApprovals.test.tsx` | 6 | loading status; empty status; safe decision fields only (never internal IDs); approve removes the row; 409 refreshes instead of faking success; load error + retry |
| `AdminDashboard.test.tsx` | 4 | loading status; real counts + audit activity; empty audit state; error + retry with exactly one request per load |
| `ResultsManager.test.tsx` | 3 | tenant sent from auth state + backend result shape; fully successful upload; upload disabled + neutral status when no institution is linked |
| `adminApi.test.ts` (modified) | 1 assertion added | pins `POST /api/v1/admin/results/csv-upload` + `FormData` body |

Net new admin tests: **24**. The pre-existing `FaqManager.test.tsx` is
unchanged and still green.

## 31. Backend Tests

`backend/tests/test_admin_experience_phase_6_19.py` — **20 tests**, in six
sections. No production backend behaviour is changed by this phase: the suite
**pins** the contract map so the frontend admin shell cannot drift into
privilege.

1. **Admin role resolution (server-authoritative, `/auth/me`)**
   - `test_resolve_primary_role_admin_precedence_unchanged`
   - `test_auth_me_returns_admin_role_with_tenant`
   - `test_auth_me_client_params_cannot_override_admin_role`
2. **Admin → admin surfaces ALLOWED (representative, tenant-scoped)**
   - `test_admin_me_returns_identity_and_status`
   - `test_admin_dashboard_scoped_to_own_tenant`
   - `test_admin_list_students_scoped_to_own_tenant`
3. **Non-admin roles → admin surfaces DENIED (403), staff exception intact**
   - `test_student_denied_admin_surfaces`
   - `test_faculty_denied_admin_surfaces`
   - `test_staff_denied_admin_surfaces_except_approval_queue`
   - `test_staff_approval_exception_remains_intact`
4. **Admin approval workflow + tenant isolation**
   - `test_admin_lists_pending_students_scoped_to_own_tenant`
   - `test_admin_foreign_institution_filter_rejected`
   - `test_admin_approves_pending_student_within_own_tenant`
   - `test_admin_cannot_approve_cross_tenant_student`
   - `test_admin_cannot_reject_cross_tenant_student`
   - `test_admin_cannot_read_cross_tenant_student`
   - `test_admin_approval_identity_params_are_inert`
5. **Results CSV upload (`POST /results/csv-upload`, tenant-scoped Form field)**
   - `test_admin_csv_upload_foreign_institution_rejected`
   - `test_admin_csv_upload_own_institution_scopes_correctly`
6. **Data minimization**
   - `test_admin_responses_expose_no_token_material`

## 32. Full Regression

All verification was run against the final state of the tree:

| Suite | Command | Result |
|---|---|---|
| Frontend typecheck | `npx tsc -b` (in `frontend/`) | **exit 0** |
| Frontend unit/behaviour | `npx vitest run` (in `frontend/`) | **45 files / 378 tests passed** |
| Backend 6.19 suite | `python -m pytest tests/test_admin_experience_phase_6_19.py -q` | **20 passed** |
| Backend admin API | `python -m pytest tests/test_admin_api.py -q` | **27 passed** |
| Backend all admin-related | `python -m pytest tests -q -k admin` | **314 passed** |

No regressions were introduced in any other role's shell: the student,
faculty, and staff suites remain part of the 378 passing frontend tests, and
the admin tests are additive to the 314 passing backend admin tests.

## 33. Git Scope

**Modified (9):**

- `frontend/src/features/admin/AdminDashboard.tsx` — loading state given
  `role="status"`.
- `frontend/src/features/admin/AdminShell.tsx` — rewritten to use the
  navigation model; adds Approvals / AI Assistant / Profile views, per-view
  `h1`, `aria-current`, and no-`<nav>`-when-empty.
- `frontend/src/features/admin/AdminShell.test.tsx` — rewritten.
- `frontend/src/features/admin/StudentManager.tsx` — tenant from
  `user.institution_id`; manual UUID input removed.
- `frontend/src/features/admin/DocumentManager.tsx` — `DEMO_INSTITUTION_ID`
  removed; tenant from identity.
- `frontend/src/features/admin/ResultsManager.tsx` — CSV upload corrected
  (route, Form field, response shape, no-tenant disabled state).
- `frontend/src/services/adminApi.ts` — `uploadResultsCsv` corrected.
- `frontend/src/services/adminApi.test.ts` — pins the corrected CSV path.
- `frontend/src/types/admin.ts` — added `CsvRowError` / `CsvUploadResult`.

**Added (10):**

- `PHASE_6_19_ADMIN_EXPERIENCE_FOUNDATION.md` (this document)
- `backend/tests/test_admin_experience_phase_6_19.py`
- `frontend/src/features/admin/adminNavigation.ts`
- `frontend/src/features/admin/adminNavigation.test.ts`
- `frontend/src/features/admin/AdminApprovals.tsx`
- `frontend/src/features/admin/AdminApprovals.test.tsx`
- `frontend/src/features/admin/AdminDashboard.test.tsx`
- `frontend/src/features/admin/AdminIdentityCard.tsx`
- `frontend/src/features/admin/AdminProfile.tsx`
- `frontend/src/features/admin/ResultsManager.test.tsx`

**No** backend production file, migration, environment file, or lock document
was modified.

## 34. Final Status & Limitations

**Status: Implemented and verified.** The admin workspace is now a
server-authoritative, production-safe surface built only on existing backend
contracts, with the verified frontend defects fixed and the whole contract
pinned by regression tests on both sides.

**Deliberate limitations (honest, not hidden):**

- **No backend surface was added.** Anything without an existing, verified
  contract is documented and unavailable rather than invented.
- **No User / Role / Institution management UI.** Those backend capabilities
  exist for admins but have no frontend manager, so no navigation entry is
  added. They are reachable server-side only.
- **No GUI router.** No router library is installed; the shell switches views
  with local state, so deep-linking a specific admin view is not supported.
- **Attendance and Test Results require a typed `student_id`.** No
  list/browse-students-then-drill-in contract is exposed by those screens
  today; the identifier is a query target that the server re-scopes.
- **No admin "learning resources" surface.** Content is curated through
  knowledge sources/documents and FAQs (§16).
- **`GET /admin/me` is intentionally unused by the shell.** Identity comes from
  the single `/auth/me` bootstrap; the endpoint remains available and is
  covered by backend tests.
- **Approval workflow is the only cross-role exception.** Staff access to the
  approval queue is pre-existing, locked Phase 6.4 policy and is unchanged.
- **No employee/HR profile model exists** for admin accounts, so the Profile
  view states that no additional details are available rather than fabricating
  them.
