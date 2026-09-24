# Phase 6.16.3 — Student Information & Learning Resource Experience

## 1. Phase Objective

Complete the remaining student-facing information surfaces established by
Phase 6.16: the **Notices** page, the **Learning Resources** page, and the
**Student Profile** page, presented as a coherent, read-only, tenant-scoped,
server-authoritative information area with correct loading/empty/error/retry
states, verified security properties (tenant isolation, student ownership,
data minimization), responsive and accessible presentation, new frontend and
backend tests, an integration journey, performance verification, full
regression, and this document.

No new backend endpoints were needed: the contract audit (Section 3) found
that every required read path already exists and is fully secured. This phase
therefore hardened, verified, documented, and tested the frontend experience
against the locked contracts, and added targeted backend guard tests.

## 2. Existing Architecture

Treated as LOCKED and untouched:

- Supabase authentication, JWT authentication, `AuthProvider`, session
  lifecycle (Phase 6.15.7: 401 → `notifySessionExpired` → AuthProvider
  sign-out), role resolution, tenant resolution, student identity.
- `StudentShell` — authenticated student frame with 7-view navigation
  (Dashboard / Attendance / Results / Notices / Learning Resources /
  AI Assistant / Profile) built on `studentNavigation.ts`.
- Student API architecture — `frontend/src/services/studentApi.ts` is the ONLY
  HTTP boundary: read-only `fetch` calls, opaque bearer token, typed
  `StudentApiError`, no mutations.
- `useStudentResource.ts` — the single data-loading primitive (one request per
  instance, generation-guarded, failure-isolated per section).
- Dashboard, attendance, results, `ChatShell`, and the RAG architecture.

## 3. Contract Audit

Verified against the codebase before any change:

| Concern | Existing contract |
|---|---|
| Student notices | `GET /api/v1/students/me/notices` (`backend/app/api/students.py`), service `app.services.student_notices`, repository `student_dashboard.list_published_notices`, schema `student_notices.StudentNoticeList` (`items[]` + `total`) |
| Notice fields | `notice_id` (list key only), `title`, `content`, `category`, `priority`, `is_pinned`, `published_at`, `expires_at` — `extra="forbid"` |
| Learning resources | `GET /api/v1/students/me/resources`, service `app.services.student_resources`, repository `list_published_resources`, schema `student_resources.StudentResourceList` |
| Resource fields | `resource_id` (list key only), `title`, `description`, `source_type`, `effective_from`, `effective_until` — `extra="forbid"` |
| Resource source types | `EXCLUDED_RESOURCE_SOURCE_TYPES = ("notice", "faq")` in the repository, provably a subset of the locked `public_chat.PUBLIC_SOURCE_TYPES = {faq, notice, handbook}` (drift-guarded by the Phase 6.16 backend suite) |
| Student profile | `GET /api/v1/students/me/academic-profile` (Phase 6.14.1): student_number, register_number, university_roll_number, email, institution_name/code, program_name/code, academic_year_name/code, current_semester_name/code, status, approval_status |
| Notice limit | `DEFAULT_NOTICE_LIMIT = 5`, `MAX_NOTICE_LIMIT = 20`, `limit` query param `ge=1, le=20` (422 `INVALID_FILTER` outside) |
| Resource limit | `DEFAULT_RESOURCE_LIMIT = 6`, `MAX_RESOURCE_LIMIT = 50`, `ge=1, le=50` |
| Notice ordering | Server-side: `is_pinned desc`, then `published_at desc` |
| Resource ordering | Server-side: `created_at desc` |
| Profile updates | **No student-owned update contract exists.** Every `PATCH /students/*` route is admin-only; the only student-owned mutation in the `/me` namespace is the unrelated Phase 6.11 notification read-receipt (`PATCH /me/notifications/{id}/read`) |

Findings: no notice detail endpoint exists (not needed — Section 8); no
notice/resource filter parameters exist beyond `limit` (so no filter UI was
invented); no storage-access/download contract exists (so no open/link action
was invented). Nothing was duplicated and no endpoint was created.
## 4. Notices Experience

`NoticesPage` (`frontend/src/features/student/StudentPages.tsx`) renders the
`NoticesPanel` inside a semantic `SectionCard` ("Notices from your
institution") and loads with `getMyNotices(token, 20)` — the backend's maximum
documented page. The dashboard keeps its compact `limit=5` section. The page
is reachable from the top navigation ("Notices") and the dashboard's
"View all notices" link. The student sees only notices the backend returns
for their own institution (published + active + unexpired) — authorization is
entirely server-side.

## 5. Notice Presentation

Each notice renders ONLY contract fields: title, plain-text content, category
label, priority label, published date (or the "not provided" dash), and a
"Pinned" badge when `is_pinned` is true. `formatLabel`/`formatText`/
`formatDate` (`studentFormat.ts`) normalize machine values safely — a
non-string or empty value renders as an em dash, never `undefined`, `null`,
`NaN`, or `[object Object]` (frontend-tested with `category: 42`,
`priority: null`). NOT exposed: internal notice IDs as visible text, creator
user IDs, institution UUIDs, audit metadata, publication flags, storage
information. Content is rendered as React text nodes — there is no
`dangerouslySetInnerHTML`/`innerHTML` anywhere in the student experience
(verified by grep and by an XSS-content test).

## 6. Notice Ordering

The backend orders pinned-first-then-newest. The panel renders every row the
backend returned in the order returned — no client-side sorting exists
(`NoticesPage.test.tsx` pins the exact server order in the DOM: "Pinned
maintenance" → "Newer notice" → "Older notice"). There is no
business-critical ordering in React.

## 7. Notice Limits

The backend contract is a bounded recent set with `limit` (1..20) and NO
pagination parameters. The Notices page requests exactly `limit=20`
(`MAX_NOTICE_LIMIT`), the dashboard `limit=5`; the UI never requests a value
outside the documented bounds and no pagination UI was invented. The bounded
"recent set" nature (no infinite scroll, no page 2) is documented here as the
intentional contract. Backend boundary tests: `limit=20` accepted,
`limit=21` → 422 `INVALID_FILTER`
(`tests/test_student_information_phase_6_16_3.py`).

## 8. Notice Detail

No dedicated backend notice-detail endpoint exists, and none is needed: the
list contract already returns the FULL notice content, so each list item IS
the detail presentation (title, full plain-text content, category, priority,
date, pinned badge). Creating a new detail endpoint merely for UI convenience
would violate the phase scope, so the limitation is documented instead: there
is no separate detail route/view, and no information is truncated by the UI.

## 9. Notice Empty State

Zero notices — a newly created institution or an all-expired corpus — renders
the neutral message "No recent notices." with no failure wording, no zero
counts, and no `role="alert"` (frontend-tested). Loading never renders an
empty state and an error never renders an empty state; the four states remain
distinct (`SectionState.tsx`).

## 10. Notice Error Handling

A failed notices request renders `role="alert"` with the user-safe message
"Unable to load notices." and a real "Try again" `<button>`. Retry re-issues
ONLY the notices request (`getMyNotices` called exactly twice; no other loader
touched — frontend-tested on both the page and the shell). Backend error
bodies never reach the DOM (the thrown internal message is replaced by the
stable section message). A notice API failure never logs the student out:
actual 401 responses raise the EXISTING Phase 6.15.7 session-expiry event
inside `studentApi.ts` and AuthProvider owns the sign-out — no second session
mechanism (journey-tested: `logout` is never called by the page).
## 11. Learning Resources Experience

`ResourcesPage` renders the `ResourcesPanel` inside a `SectionCard` ("Learning
resources") and loads with `getMyResources(token, 20)` (≤ `MAX_RESOURCE_LIMIT`
50). Reachable from the top navigation ("Learning Resources") and the
dashboard's "View all resources" link. Only rows the backend authorized for
the student's own institution (published lifecycle, notice/faq source types
excluded server-side) are shown.

## 12. Resource Metadata

Each resource renders ONLY: title, description (when present), source-type
label, and the "Effective from" date (dash when absent). `effective_until`,
`total`, and `resource_id` are never rendered. NOT exposed: storage keys,
bucket names, internal object paths, signed URLs, internal database IDs,
service/pipeline metadata — verified by a DOM test that injects
`storage_bucket`, `storage_object_key`, `document_id`, and `institution_id`
into a response row and asserts none appear (backend `extra="forbid"` guards
the same boundary from the other side).

## 13. Resource Source Types

The panel renders whatever `source_type` the backend returns, through
`formatLabel` — it does NOT maintain a second frontend source-type list. The
backend vocabulary (`PUBLIC_SOURCE_TYPES` minus notice/faq) is drift-guarded
by the existing Phase 6.16 backend test. An unknown source type (e.g.
`"mystery-pack"`) renders as "Mystery pack" without crashing; a non-string
value renders as the em-dash fallback — both frontend-tested, and the backend
side is pinned by
`test_source_type_outside_the_known_vocabulary_is_projected_safely`.

## 14. Resource Access

The existing backend provides NO storage-access, download, or URL contract
for student-facing resources (deliberately — storage internals must not
leak). Therefore the page renders safe metadata with NO open/link/download
action, constructs no storage URLs, exposes no R2 internals, and generates no
client-side signed URLs. This limitation is documented here as intentional;
opening resource content remains a future backend contract.

## 15. Resource Limits

The page requests `limit=20`, inside the documented 1..50 bound; the dashboard
requests `limit=6`. No unlimited request exists. Backend boundary tests:
`limit=20` accepted (and `MAX_RESOURCE_LIMIT` ≥ 20 asserted), `limit=51` →
422 `INVALID_FILTER`. The API layer enforces `ge=1, le=50` via the FastAPI
`Query` declaration (422 outside, Phase 6.16-tested).

## 16. Resource Empty State

Zero resources renders "No learning resources are currently available." —
neutral, no failure implication, no misleading zero count, no
`role="alert"` (frontend-tested).

## 17. Resource Error Handling

Same four-state discipline as notices: `role="alert"` "Unable to load
learning resources." + "Try again". Retry re-issues ONLY the resources
request (`getMyResources` twice; `getMyNotices` never called —
frontend-tested). Attendance, results, profile, and authentication state are
unaffected by a resources failure (per-section state isolation in
`useStudentResource`). 401 handling is identical to Section 10.
## 18. Student Profile

`ProfilePage` renders two sections over ONE shared `getMyAcademicProfile`
request (one request per profile mount): "Your profile" (`StudentIdentityCard`)
and "Academic context" (`AcademicContextCard`), each inside a semantic
`SectionCard`. Both consume the existing `GET /students/me/academic-profile`
Phase 6.14.1 contract only — no other profile endpoint exists and none was
created.

## 19. Academic Identity

The identity card presents, as a semantic definition list (`<dl>` with
`<dt>/<dd>` pairs): Email, Register number, University roll number, Student
number, Institution name, Institution code, Enrollment status, Approval
status — every field the backend contract actually returns. The card greets
the student by their preferred academic identifier (register number → roll
number → student number) because the `students` table carries no verified
name column — a documented, intentional gap the UI does not paper over with a
fabricated name. NOT exposed: auth user UUID, student database UUID,
institution UUID, JWT, approval implementation metadata, or any internal
audit field (none of these exist in the frontend type, and a DOM test
injects them into a response and asserts they never render).

## 20. Profile Editing

READ-ONLY BY DESIGN. The contract audit (Section 3) verified there is NO
student-owned profile-update contract: every `PATCH /students/{student_id}`
route is admin-only, and the only student-owned mutation in the `/me`
namespace is the unrelated Phase 6.11 notification read-receipt. No
PATCH/PUT endpoint was created to make the UI editable, and the profile page
contains no form controls whatsoever (frontend-tested: zero
`input/textarea/select/button` elements and no "Edit"/"Save" affordances in
the loaded state).

## 21. Academic Context

The context card shows ONLY backend-resolved context: Institution
(name + code), Program (name + code), Academic year (name + code), Current
semester (name + code). Profile, Dashboard, Attendance, and Results all read
the SAME server-provided academic context from the same Phase 6.14.1
contract — there is no frontend calculation of current semester, academic
year, student year, or graduation year anywhere. Department, year-of-study,
and section are NOT displayed because the backend contract does not expose
them (displaying them would require inventing values); any field the backend
returns as `null` renders as the explicit "not provided" em dash.

## 22. Tenant Isolation

All three surfaces authorize server-side. The backend chain is: authenticated
JWT → `get_current_user` → `student_context.get_student_context` (students
row resolved from users.user_id; approved + active + institution active) →
`assert_student_context_tenant` (defence-in-depth tenant match) →
`list_published_notices` / `list_published_resources` with the student's OWN
institution id as a mandatory equality filter. A student of Institution A
structurally cannot receive Institution B's notices or resources, and
`student_dashboard.list_*` require `institution_id` as a mandatory argument.
Existing Phase 6.16 backend tests pin this
(`test_notice_query_never_spans_institutions`,
`test_client_supplied_institution_cannot_widen_the_scope`,
`test_notices/resources_return_only_the_authenticated_students_institution`).

## 23. Student Ownership

Every `/students/me/*` endpoint resolves identity from the authenticated JWT
only; none accepts a client-supplied identity parameter. There is no
`/students/profile?student_id=...` style route anywhere, and the services
(`student_notices`, `student_resources`, `student_academic_profile`) expose no
identity parameter a client could control
(`test_services_expose_no_identity_parameter`,
`test_client_supplied_student_id_cannot_override_identity`, Phase 6.16.2
suite). A client-supplied `institution_id`/`student_id` query value is
ignored (and schema `extra="forbid"` rejects smuggled fields with 422).

## 24. Data Minimization

Verified at three layers. (1) HTTP: response schemas use `extra="forbid"`
and deliberate projections that exclude `institution_id`, `created_by`,
`is_active`/`is_published`, storage keys/buckets/checksums, and every
internal identifier except the stable `notice_id`/`resource_id` list keys
(backend-tested, including
`test_models_reject_smuggled_internal_identifiers`). (2) DOM: the frontend
types do not even contain the internal fields, and tests inject
`student_id`, `user_id`, `auth_user_id`, `institution_id`, `created_by`,
`storage_bucket`, and `storage_object_key` into mocked responses and assert
they never render (Notices/Resources/Profile/Dashboard tests). (3) React
keys: `notice_id`/`resource_id` are used as stable list keys only and are
asserted absent from `container.innerHTML`. A non-React-key DOM value that
matches an internal identifier fails the suite.
## 25. Responsive Design

Built on the existing shell layout (`max-w-6xl` centered content, `px-4`
gutters, `flex-wrap` navigation, `overflow-x-clip` root):

- Mobile (single column): long notice titles/content and long resource
  titles wrap via `break-words`/`min-w-0`; notice/resource cards are full
  width; profile definition pairs collapse to one column (`grid-cols-1`);
  the top navigation wraps into multiple rows; no page-level horizontal
  overflow.
- Tablet (`sm:` breakpoint): profile fields and academic context render as a
  two-column definition grid; resource and notice cards keep readable
  measure; spacing scales (`sm:p-5`).
- Desktop: content constrained to a readable width inside `max-w-6xl`;
  consistent card spacing; text line lengths remain readable.

All layout is CSS-flex/grid — no fixed pixel widths on text containers.

## 26. Accessibility

- Semantic page `h1` per view (`STUDENT_VIEW_HEADINGS`) and one `h2` per
  section via `SectionCard` with `aria-labelledby`.
- Navigation is a real `<nav aria-label="Student navigation">` landmark with
  `<button>` items and `aria-current="page"` on the active view.
- Loading states use `role="status"` (polite), errors use `role="alert"`,
  and retry controls are real text-labelled `<button>` elements — no
  colour-only signalling (all `SectionState.tsx` primitives, reused).
- Notice list is a semantic `<ul>`; profile fields are semantic
  `<dl>/<dt>/<dd>` labelled pairs — read-only text, NOT fake disabled form
  controls.
- Keyboard: every interactive element is a native `<button>` (Tab + Enter);
  visible focus rings via `focus:outline-none focus:ring-2` throughout the
  shell and retry buttons.
- No `dangerouslySetInnerHTML`/`innerHTML` anywhere in the student
  experience.

## 27. Frontend Tests

New suites (all passing):

- `NoticesPage.test.tsx` (8): page renders + all fields; server ordering
  preserved in DOM; `limit=20` requested; loading; neutral empty; error +
  retry isolation; safe content rendering (XSS text, injected
  `institution_id`/`created_by`, `notice_id` never in DOM); malformed
  category/priority fallback.
- `ResourcesPage.test.tsx` (8): page renders + metadata; unknown source type
  safe; non-string source type em-dash fallback; `limit=20`; loading; empty;
  error + retry isolation; storage-internals injection test + zero
  link/button (no access action).
- `ProfilePage.test.tsx` (7): identity renders; academic context renders;
  missing optional fields → em dashes; injected internal IDs never render;
  read-only (no controls, no Edit/Save); loading; error + retry.
- `StudentInfoJourney.test.tsx` (4): full 7-step navigation journey with
  exact per-mount request counts; dashboard ViewLinks + back navigation;
  retry isolation; 401 → retryable section error, `logout` never called.

Existing suites kept green (dashboard, states, hardening, edge cases,
shell-nav, detail pages, API client, App).

## 28. Backend Tests

New guard suite `backend/tests/test_student_information_phase_6_16_3.py`
(6 tests, passing):

- Notices page limit boundary (`MAX_NOTICE_LIMIT` accepted; +1 → 422
  `INVALID_FILTER`).
- Resources page limit boundary (20 accepted with `MAX_RESOURCE_LIMIT ≥ 20`
  asserted; +1 → 422).
- Unknown source type projected safely with exact contract keys and zero
  storage/tenant leakage.
- No student-owned mutation route for academic-profile / notices / resources
  (OpenAPI paths are GET-only; the unrelated Phase 6.11 notification
  read-receipt PATCH is explicitly out of scope).

Existing coverage NOT weakened, and relied upon:
`tests/test_student_experience_dashboard_phase_6_16.py` (tenant scoping,
publication filtering, projections, identity resolution, eligibility, empty
data, API limits, data minimization, admin boundary, authorization),
`tests/test_academic_profile_6141.py` (own profile, no internal IDs, unauth,
cross-token, cross-tenant), `tests/test_student_academic_detail_phase_6_16_2.py`
(identity-parameter security, data minimization).
## 29. Integration Tests

`StudentInfoJourney.test.tsx` covers the required journey end-to-end over the
real `StudentShell` + page composition (API boundary mocked):

    Authenticated student → Dashboard → Notices → Dashboard →
    Learning Resources → Dashboard → Profile → Dashboard

with per-view headings, content assertions, and EXACT request counts (one
request per section mount; no duplicates from rendering; no uncontrolled
navigation requests). Session expiry is covered by the 401 scenario: the
notices request returns 401 → the page shows a retryable section error →
the page never calls `logout` itself; the transition to the login screen
belongs to the EXISTING chain (real API client raises
`notifySessionExpired` → `AuthProvider` signs out → login screen renders),
unchanged and covered by the Phase 6.15.7 / 6.16 suites. No second session
mechanism exists. (The app has no router library: navigation is shell view
state, so a refresh deterministically re-enters at the Dashboard.)

## 30. Performance

Measured via mocked-call counts in the integration suite:

- Notices initial requests: dashboard 1 (`limit=5`); Notices page 1
  (`limit=20`).
- Resources initial requests: dashboard 1 (`limit=6`); Resources page 1
  (`limit=20`).
- Profile initial requests: dashboard 1 (shared by identity + context
  cards); Profile page 1.
- Duplicate requests: NONE per mount (each section/hook instance issues
  exactly one request; assertions pin exact totals across the full journey:
  5× profile, 5× notices, 5× resources, 4× attendance for the 7-step
  journey).
- Navigation creates no uncontrolled requests (exact-count assertions);
  retry retries ONLY the failed section; no polling, no speculative caching
  layer was introduced (remount refetches are the documented, intentional
  behaviour of the stateless loader).

## 31. Regression Testing

All green after the phase:

- Backend: `python -m pytest tests -q` → **1807 passed, 15 skipped**.
- Frontend: `npx vitest run` → **33 files, 294 tests passed**.
- TypeScript: `npx tsc -b` → clean.
- Production build: `npm run build` → success (pre-existing Tailwind CSS
  pseudo-class warning only, unrelated to this phase).

## 32. Git Scope

Modified (tracked, comments only): `frontend/src/features/student/StudentPages.tsx`
(contract documentation comments on the three pages; zero behavioural change).

Added: `frontend/src/features/student/NoticesPage.test.tsx`,
`frontend/src/features/student/ResourcesPage.test.tsx`,
`frontend/src/features/student/ProfilePage.test.tsx`,
`frontend/src/features/student/StudentInfoJourney.test.tsx`,
`backend/tests/test_student_information_phase_6_16_3.py`, and this document.

Unrelated files modified: NONE. Commit created: **NO** (per phase
instructions).

## 33. Phase Completion Status

- Notices experience: DONE (page verified against the existing contract).
- Notice presentation: DONE (safe fields only, XSS-safe rendering tested).
- Notice ordering: DONE (server order pinned in DOM tests).
- Notice limits: DONE (20 = documented max; backend boundary-tested).
- Notice detail: N/A — documented limitation (full content already inline).
- Notice loading/empty/error/retry: DONE (all four states tested).
- Learning Resources experience: DONE.
- Resource metadata: DONE (minimized, injection-tested).
- Resource source types: DONE (backend vocabulary only; unknown types safe).
- Resource access: existing safe contract only — metadata without any
  storage action; limitation documented.
- Resource limits: DONE (20 ≤ 50; backend boundary-tested).
- Resource loading/empty/error/retry: DONE.
- Student Profile: DONE.
- Academic identity: DONE (backend fields only; internal IDs never rendered).
- Profile editing: READ-ONLY (no update contract exists — intentional,
  documented, tested).
- Academic context: backend-authoritative (no frontend calculation).
- Tenant isolation: VERIFIED (server-side, existing tests + guards).
- Student ownership: VERIFIED (JWT-derived identity only; no identity params).
- Data minimization: VERIFIED (HTTP + DOM + React-key layers tested).
- Responsive behavior: VERIFIED (mobile/tablet/desktop layout rules).
- Accessibility: VERIFIED (landmarks, semantics, roles, keyboard, focus).
- Frontend tests: 294/294 PASS (including 27 new).
- Backend tests: 1807 passed / 15 skipped (including 6 new).
- Integration tests: DONE (7-step journey + session expiry).
- Performance: REVIEWED (one request per section mount; no duplicates).
- Full regression: PASS. TypeScript: PASS. Production build: PASS.
- Documentation: this file — exactly 33 sections.
- Git scope: documented; no unrelated files; NO commit created.

**Phase 6.16.3 — COMPLETE.** Stopping per the strict stop condition: no
Phase 6.16.4, no Phase 6.17, no faculty/staff dashboards, no mobile app, no
chatbot/auth redesign, no new infrastructure, no commit.






