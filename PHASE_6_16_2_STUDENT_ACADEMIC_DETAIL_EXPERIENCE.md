# Phase 6.16.2 — Student Academic Detail Experience

> Read-only attendance + results detail pages over the EXISTING `/students/me/*`
> contracts. Backend stays authoritative for every academic calculation and for
> authorization. No endpoint, table, or auth rule is added or changed by this
> phase; the only contract extension is an OPTIONAL client-side query-option
> surface (`date_from` / `date_to`) on top of the existing
> `GET /students/me/attendance/summary` filter contract.

## 1. Phase Objective

Build and harden the detailed student-facing academic experience for:

- Attendance
- Examination/Test Results

Phase 6.16 and 6.16.1 already provide: student dashboard, attendance overview,
results overview, student navigation, tenant isolation, student authorization,
resilient loading/error/empty states, responsive and accessible UI.

This phase extends those capabilities into complete read-only academic detail
pages. The student moves:

```text
Dashboard → Attendance overview → Detailed Attendance
Dashboard → Results overview    → Detailed Results
```

The backend remains authoritative for all academic calculations and
authorization.

## 2. Existing Architecture

Locked and reused verbatim (no redesign):

- Supabase Auth + JWT authentication + AuthProvider.
- `session-expiry` events (`services/sessionEvents.ts`): any authenticated 401
  publishes `notifySessionExpired(accessToken)`; AuthProvider clears the
  session and the login screen takes over. No second session mechanism.
- Server-authoritative role resolution (`GET /auth/me` → `user.role`).
- Tenant resolution from the JWT chain (`users.user_id → students.user_id →
  students.institution_id`).
- Student identity from the JWT (`users.user_id → students.user_id`); there is
  NO `student_id` / `user_id` / `institution_id` parameter on any `/me/*` path.
- Existing attendance APIs, results APIs, `StudentShell`, dashboard,
  `ChatShell` — all reused, none redesigned.

## 3. Contract Audit

Exact existing endpoints (no names invented, verified in
`backend/app/api/students.py`):

| Purpose | Endpoint | Query fields (server-side) | Response model |
|---|---|---|---|
| Academic identity + context | `GET /api/v1/students/me/academic-profile` | none (JWT only) | `StudentAcademicProfile` |
| Attendance summary + records | `GET /api/v1/students/me/attendance/summary` | `academic_year_id`, `semester_id`, `date_from`, `date_to` (fixed server cap 200, no `limit` param) | `StudentOwnAttendance` |
| Published academic results | `GET /api/v1/students/me/results/summary` | `academic_year_id`, `semester_id` | `StudentOwnResults` |
| Published per-test scores | `GET /api/v1/students/me/test-results/summary` | `academic_year_id`, `semester_id` (fixed server cap 100, no `limit` param) | `StudentOwnTestResults` |
| Published academic result detail | `GET /api/v1/students/me/results/{result_id}` | `result_id` path | `StudentAcademicResultDetail` |
| Legacy own rows (unchanged) | `GET /api/v1/students/me/attendance`, `/me/results`, `/me/test-results` | same filters | raw rows |

Response fields (from `backend/app/schemas/` — nothing invented):

- `StudentAttendanceSummary`: `records_available`, `total_classes`,
  `present_classes`, `absent_classes`, `late_classes`, `excused_classes`,
  `attendance_percentage` (server-computed, `None` when zero records).
- `StudentAttendanceRecord`: `date`, `status`, `notes` — no subject, period,
  internal ids.
- `StudentOwnResultsSummary` / `StudentOwnTestResultsSummary`:
  `records_available`, `total_results` — counts only, no aggregates.
- `StudentAcademicResultRecord`: `result_type`, `total_credits_earned`,
  `total_credits_max`, `sgpa`, `cgpa`, `status` (always `published`), `issued_at`.
- `StudentTestResultRecord`: `test_name`, `test_type`, `course_code`,
  `course_name` (benign labels for own rows only), `max_marks`,
  `scored_marks`, `percentage`, `letter_grade`, `conducted_at`.
- `StudentAcademicProfile`: `student_number`, `register_number`,
  `university_roll_number`, `email`, `institution_name/code`,
  `program_name/code`, `academic_year_name/code`,
  `current_semester_name/code`, `approval_status`, `status` — NO internal ids,
  NO department/section fields exist.

Academic year / semester: the summary endpoints accept `academic_year_id` /
`semester_id` UUID filters, BUT no student-accessible contract exposes those
IDs — the academic profile returns names/codes only. Consequence (Sections 6,
14): the UI never sends year/semester identifiers (no invented identifier
sources) and performs no frontend-only filtering of security/tenant scope.

Schemas reject extras (`extra="forbid"`); services project whitelisted fields
only; all `/students/me/*` routes take `current_user` first with no identity
parameters (asserted by tests).

## 4. Attendance Detail

`frontend/src/features/student/AttendanceDetail.tsx` —
`AttendanceDetailPage`, wired as `AttendancePage` in `StudentPages.tsx`:

```text
Attendance
────────────────────────────
Academic context   (same /me/academic-profile contract as dashboard)
Overall summary    (server-computed figures, displayed verbatim)
Filters            (server-side date range: date_from / date_to only)
Attendance records (student-safe rows: date / status / notes)
```

Read-only by construction: the page only ever GETs
`/students/me/attendance/summary` + `/students/me/academic-profile`. No
marking/editing control exists and no student write path exists in the
backend. The dashboard keeps its compact `AttendancePanel`; the detail page is
a separate, fuller experience (filter + full table + limit note).

## 5. Attendance Summary

Backend values displayed directly, never recomputed: Overall percentage
(`attendance_percentage`, `None` → em dash), Present, Absent, Classes
recorded, plus `late/excused` only when the backend reports non-zero. No
`present/total` arithmetic exists in React (pinned by the `33.33%` verbatim
test). No backend business logic is duplicated.

## 6. Attendance Filters

Server-side date range only, using the exact supported filter fields:
`StudentAttendanceFilters` (`dateFrom` → `date_from`, `dateTo` → `date_to`);
blanks omitted; server validates (`422 INVALID_FILTER`). One serialized
`watchKey` per selection → exactly ONE new request per Apply/Reset (asserted).
The `academic_year_id` / `semester_id` endpoint filters are NOT surfaced — no
student contract exposes those IDs, so sending them would invent identifier
sources; frontend-only narrowing of scope is forbidden. Date filtering here is
NOT security-sensitive: the endpoint scopes to the student's own rows first.

## 7. Attendance Records

Accessible table (`caption` "Your attendance records", `scope="col"` headers
Date / Status / Notes) rendering ONLY returned fields: Date (ISO → locale
short date), Status (verbatim label), Notes (em dash when absent). Any
backend-supported status renders per contract (`Excused leave` from
`excused_leave` — underscore/whitespace normalization only, never new
semantics). Colour is decorative; status text carries the meaning.


## 8. Attendance Limits

The existing endpoint has a FIXED server-side cap of 200 records per response
(service constant) and exposes NO `limit`/`offset`/`cursor` parameter — so no
pagination protocol was invented and the UI cannot request an unreasonable
limit by construction: it never sends a limit at all and the server cap stays
authoritative. The detail page renders what the single bounded response
returns. If a future phase adds cursor pagination, this page can adopt it
without contract changes elsewhere.

## 9. Attendance Empty State

Two distinct, neutral empty states (pinned by tests):

- No records at all (e.g. newly approved student): "No attendance records are
  available yet." — the summary figures are NOT rendered, so the page never
  implies "0%", "0", or "Absent" merely because no data exists.
- Empty selection (a filter matched nothing): "No attendance records are
  available for this selection." — never conflated with "no records ever".

No fabricated failure/pass-fail language appears in either state.

## 10. Attendance Error Handling

`useStudentResource` states: `idle` → `loading` → `loaded` | `error`.
An attendance failure renders a `role="alert"` error block with a retry button
scoped to ONLY the attendance request (the academic-profile resource is not
reloaded — asserted: profile called once across a retry). A failed attendance
request NEVER logs the student out and never reloads the app: even a 401 is
surfaced as a section error while the EXISTING `session_expired` event (raised
inside the API client, owned by AuthProvider) handles the session transition.
A backend `422 INVALID_FILTER` (e.g. `date_from > date_to`) surfaces as a
retryable section error with the session intact.

## 11. Attendance Read-Only Security

- Backend: no POST/PUT/PATCH/DELETE route exists anywhere under
  `/students/me/attendance*`; the router only registers GETs
  (`backend/app/api/students.py`), and `backend/tests/
  test_student_academic_detail_phase_6_16_2.py` asserts 405 for mutation
  attempts on the attendance summary path with a student JWT.
- Frontend: the page's only interactive elements are the two date inputs and
  Apply/Reset buttons (asserted: button list, input types, no select/textarea);
  there is no marking/edit control and the student API module contains no
  attendance mutation function.

## 12. Results Detail

`frontend/src/features/student/ResultsDetail.tsx` — `ResultsDetailPage`, wired
as `ResultsPage` in `StudentPages.tsx`:

```text
Results
────────────────────────────
Academic context (same /me/academic-profile contract as dashboard)
Result summary   (backend counts only)
Results          (two independent sections: examination results, test scores)
```

Read-only by construction: only GETs to `/students/me/results/summary`,
`/students/me/test-results/summary` and `/students/me/academic-profile`. Each
results section is its own `useStudentResource` instance, so sections load and
fail independently.

## 13. Result Categories

Exactly the categories the backend model exposes — nothing invented:

- Published academic results (`results/summary`): semester-type records with
  SGPA/CGPA/credits and an always-`published` status.
- Published test results (`test-results/summary`): per-test scores with marks,
  percentage, letter grade.

The backend has no internal-assessment or other category contract, so none is
rendered. Both tables label themselves with captions ("Your published
examination results" / "Your published test scores").

## 14. Results Filters

## 15. Result Records

Only backend-provided fields render — exam table: Result type, Credits earned,
Credits max, SGPA, CGPA, Status, Issued; test table: Test, Course
(name, code fallback), Marks (`scored/max`), backend percentage (shown only
when finite), Grade, Conducted date. Absent values render as an em dash. The
frontend fabricates NOTHING: no grades, percentages, ranks, GPA, averages or
pass/fail status are computed or inferred (pinned by the record-integrity tests,
which feed malformed/partial rows and assert dashes, never invented numbers).

## 16. Results Summary

The backend summaries are counts-only (`records_available`, `total_results`)
and are displayed verbatim; the summary row renders ONLY when
`records_available` is true. No frontend aggregation, "latest result", or
"completed tests" derivation exists because no such backend value exists.

## 17. Results Empty State

Per-category neutral empty states: when `records_available` is false (or the
record array is empty) the section shows "No examination results are available
yet." / "No test scores are available yet." The page never displays 0%, 0
marks, or "Fail" for an absent dataset (asserted), and there is no fabricated
"incomplete academic history" language — the absence of data is stated as-is.
A summary that claims `records_available: true` with zero records is also
treated as empty defensively.

## 18. Results Error Handling

Each section is an independent resource: an examination-results failure leaves
test scores loading/loaded on its own state, and vice versa. Errors render as
`role="alert"` blocks with per-section retry buttons; a retry refetches ONLY
that section (asserted per-loader call counts). Any results API error —
including 401/404/500 — never ends the authenticated session from the page;
the existing `session_expired` event channel remains the sole logout path.

## 19. Academic Context

Attendance, results and the dashboard all render the SAME
`GET /students/me/academic-profile` contract through the shared
`AcademicContextCard` (Institution, Program, Academic year, Current semester —
name + code when both exist). There is NO second frontend concept of "current
semester"/"current academic year": the backend resolves the context and the UI
displays it verbatim. The detail pages reuse the SAME loaded profile resource
as the shell flow (one profile request per page mount, not per card).

## 20. Navigation

Verified in the integration suite against the real `StudentShell`:

- Dashboard → Attendance (via the existing "View all attendance" action) and
  Dashboard → Results ("View all results"); active nav state follows the
  existing `studentNavigation` model; back-navigation returns to the dashboard
  via the existing nav controls; browser back/forward and direct-URL entry work
  because the pages are plain route components over the existing shell (refresh
  re-runs session restoration through AuthProvider). Mobile navigation is the
  unchanged shell drawer. No privileged navigation is exposed — the nav model
  is unchanged from Phase 6.16.1.

## 21. Tenant Isolation

Server-enforced on every `/students/me/*` route: JWT identity →
`students.user_id` ownership → `institution_id` scope, chained inside
`get_current_user` + the service layer; the frontend performs no scope
filtering. Backend tests assert: a student's own attendance/results return
200; rows are always scoped to the caller's own student record and institution
(the existing `test_attendance_6142.py`, `test_results_6143.py`,
`test_tenant_isolation.py` suites were extended, not weakened). There is no
route by which Student A can request Institution B's attendance or results.

## 22. Identity Parameter Security

All detail endpoints keep authenticated `/me` semantics. The frontend never
sends `student_id`, `user_id` or `institution_id` — the loaders pass only the
access token plus the whitelisted filter fields (pinned: the recorded API-call
argument lists contain token-only and token+date fields, nothing else). The
backend rejects/ignores any identity-shaped query parameter because the schemas
forbid extras, and the new backend tests assert the `/me/*` handlers take no
identity parameters. The forbidden pattern
`/student/attendance?student_id=…` does not exist anywhere.

## 23. Data Minimization

Response schemas expose only student-safe fields: no internal student ids, no
auth user ids, no institution UUIDs, no primary keys, no audit/service/storage
metadata. The only stable keys anywhere (`notice_id`, `resource_id`) predate
this phase and are never rendered. Attendance records carry date/status/notes
only; the frontend additionally defends in depth — a test injects fabricated
internal fields (`attendance_id`, `student_id`, `institution_id`, `marked_by`)
into a response and asserts none of them ever reaches the DOM.

## 24. Responsive Design

- Mobile: summary grids collapse to 2 columns, filter controls stack with
  `flex-wrap`, tables live in `overflow-x-auto` wrappers with `min-w-*`
  floors; long notes/course names wrap or truncate inside cells.
- Tablet/desktop: `sm:grid-cols-4` summary, `sm:grid-cols-2` context, tables
  use their full width. Page-level horizontal overflow is prevented by the
  root `overflow-x-clip` (asserted by class checks in both page suites, plus
  the long-record and long-name tests).


No filter control is exposed, and this is a documented contract decision, not
an omission: the endpoints accept only `academic_year_id` / `semester_id`
UUIDs, and NO student-accessible contract returns those identifiers (the
academic profile returns names/codes only). Surfacing a selector would require
inventing an identifier source; client-side narrowing of a security/tenant-
scoped dataset is forbidden. Tests pin that the loaders receive the token only
and that the page renders zero inputs/selects/forms.

## 25. Accessibility

- Semantic `h1` page headings ("Attendance" / "Results") and a shared
  "Academic context" `h2`; the shell provides the navigation landmark.
- Every filter input has a programmatic label ("From date" / "To date"); the
  filter is a real labelled `form`.
- Tables use `caption` + `scope="col"` headers with meaningful column names.
- Loading (`.role="status"` live regions), errors (`role="alert"`), and empty
  states are announced; retry buttons are real named buttons.
- Status is never colour-only: "Present"/"Absent"/grades render as text
  alongside any styling; focus rings are explicit (`focus:ring-*`) on all
  interactive elements; everything is keyboard-operable (date inputs +
  buttons, exercised via `userEvent`).

## 26. Frontend Tests

- `AttendanceDetail.test.tsx` (16): render/context/summary/records; server-side
  filter params (`date_from`/`date_to`) + single-request-per-change + reset;
  column headers; verbatim status rendering; long notes + scroll containment;
  responsive layout; data-minimization injection; zero mutation controls;
  both empty states; loading announcement; error + scoped retry (session
  preserved, profile not refetched); 422 filter rejection; 401 surfaced as
  section error.
- `ResultsDetail.test.tsx` (14): render of context/summary/both categories;
  verbatim marks/percentage/grade; column headers; token-only loaders (no
  invented filter params); zero filter controls; per-category empty states;
  loading/error/retry independence; record-integrity (malformed rows render
  dashes, no invented grades/percentages); data minimization; no mutation
  controls.
- `StudentAcademicDetailIntegration.test.tsx` (2): the full
  dashboard → attendance → filter → dashboard → results → dashboard journey
  over the real shell (one request per navigation, filters serialized
  server-side), and the 401-on-detail → existing `session_expired` event →
  login-screen transition.

## 27. Backend Tests

`backend/tests/test_student_academic_detail_phase_6_16_2.py` adds, for BOTH
attendance and results: authenticated student access (200 with student JWT);
tenant isolation + student ownership (own rows only, other-tenant data never
leaks); filter validation (`422 INVALID_FILTER` for bad `date_from`/`date_to`,
unknown query fields rejected by `extra="forbid"`); limit behaviour (fixed
server caps, no client `limit` honoured); read-only enforcement (405 on
POST/PUT/PATCH/DELETE attempts against the summary paths); and data
minimization (response key whitelists contain no internal identifiers).
Existing suites (`test_attendance_6142.py`, `test_results_6143.py`,
`test_academic_profile_6141.py`, `test_tenant_isolation.py`,
`test_student_experience_dashboard_phase_6_16.py`) were extended only where
noted and never weakened.

## 28. Integration Tests

`StudentAcademicDetailIntegration.test.tsx` covers the realistic flow:
authenticated student → dashboard → attendance detail → server-side attendance
filter → back to dashboard → results detail → back to dashboard, asserting
exact request counts at every hop (no duplicates, no background churn). The
session-expiry flow is also integrated: a 401 on an academic detail request
publishes the EXISTING `session_expired` event, AuthProvider clears the
session, and the login screen appears — no second session mechanism.

## 29. Performance

Measured with mock-call counts in the suites (no speculative caching added):

- Attendance: 1 request per page mount; exactly 1 additional request per
  filter Apply/Reset (serialized `watchKey` prevents double-fires).
- Results: 1 request per section (2 total) per mount; no filter churn
  (no filters exist).
- Navigation: opening a detail page from the dashboard reuses the shell and
  issues only the detail page's own requests (dashboard requests are not
  re-issued); returning to the dashboard re-mounts it with its normal
  per-section requests and nothing else.
- Refresh: AuthProvider restores once (`/auth/me`), then the shell's normal
  single round of requests; no duplicate initialization.

## 30. Regression Testing

Full green run at phase close:

- Backend: `python -m pytest tests -q` → **1801 passed, 15 skipped**
  (~46 s), 7 pre-existing third-party deprecation warnings.
- Frontend: `npx vitest run` → **267 passed** (26 files, includes the 32 new
  6.16.2 tests); `npx tsc -b` → clean; `npm run build` → succeeds
  (~5 s, one pre-existing CSS_optimizer pseudo-class warning unrelated to this
  phase).

## 31. Git Scope

Changed (tracked): `frontend/src/services/studentApi.ts` (optional
`StudentAttendanceFilters` date-range query options on the EXISTING attendance
loader), `frontend/src/features/student/useStudentResource.ts` (generic
query-options support, no behaviour change), `frontend/src/features/student/
StudentPages.tsx` (Attendance/Results routes now render the detail pages).
Added (untracked): `frontend/src/features/student/AttendanceDetail.tsx`,
`ResultsDetail.tsx`, their two test files, `StudentAcademicDetailIntegration
.test.tsx`, `backend/tests/test_student_academic_detail_phase_6_16_2.py`, and
this document. No unrelated files modified; no commit created by this phase.

## 32. Phase Completion Status

COMPLETE — all Definition-of-Done items verified: attendance detail (summary
from backend values, contract filters, records, limits, empty/loading/error/
retry, read-only), results detail (categories, filters decision, records,
counts-only summary, empty/loading/error/retry, read-only), no frontend
academic calculations, backend-authoritative academic context, navigation,
tenant isolation, identity-parameter security, data minimization, responsive +
accessibility verification, frontend/backend/integration tests, TypeScript,
production build, full regression, and exactly these 32 sections. Phase
6.16.3 and 6.17 NOT started.

