# PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING

Status: Phase 6.16.1 complete (verification report at the end of this file). No commit created — all changes remain in the working tree.

## 1. Phase Objective

Harden the completed Phase 6.16 student experience without expanding the
product into new roles or new major features. The focus is correctness and
UX resilience: the dashboard must stay correct when real-world data is
incomplete, large, delayed, duplicated, stale, malformed, or partially
unavailable. No feature expansion, no new roles, no backend redesign.

## 2. Existing Dashboard Architecture

Everything below is reused verbatim and locked (no redesign):

- `StudentShell` (`frontend/src/features/student/StudentShell.tsx`) — authenticated student frame + 7-view navigation.
- `studentNavigation.ts` — Dashboard, Attendance, Results, Notices, Learning Resources, AI Assistant, Profile.
- `StudentDashboard.tsx` + `StudentPages.tsx` — dashboard overview + full pages.
- Six panels: `StudentIdentityCard`, `AcademicContextCard`, `AttendancePanel`, `ResultsPanel`, `NoticesPanel`, `ResourcesPanel`.
- `SectionState.tsx` — shared loading / empty / error primitives (`LoadingBlock`, `EmptyBlock`, `ErrorBlock`, `SectionCard`, `Definition`, `NOT_PROVIDED`).
- `studentFormat.ts` — pure display formatters; no calculation, no invented values.
- `useStudentResource.ts` — the single data-loading primitive (one request per instance, generation-guarded, failure-isolated per section).
- `services/studentApi.ts` — the only HTTP boundary; read-only; browser-native `fetch`; Phase 6.15.7 session lifecycle reused (401 → `notifySessionExpired` → AuthProvider sign-out).
- `types/student.ts` — frontend mirror of the backend `extra="forbid"` Pydantic schemas.
- Backend `backend/app/api/students.py` `/students/me/*` endpoints with server-side identity + tenant resolution.
- Existing `ChatShell` AI-assistant entry point (untouched).

The dashboard remains strictly a consumer of these contracts.

## 3. Dashboard Request Map

Six concurrent `GET` requests fire on dashboard initialization — one per
`useStudentResource` instance (React runs each instance's effect
independently, so the loads run concurrently, not chained):

| Request | Required Auth | Tenant Scoped | Limit | Ordering | Empty Allowed |
| --- | --- | --- | --- | --- | --- |
| `GET /api/v1/students/me/academic-profile` | Bearer JWT (`get_current_user`) | Yes (server-resolved) | n/a | n/a | Yes (all fields optional) |
| `GET /api/v1/students/me/attendance/summary` | Bearer JWT | Yes | 200 records (server default) | Most recent day first | Yes (`records_available=false`, `[]`) |
| `GET /api/v1/students/me/results/summary` | Bearer JWT | Yes | 100 records (server default) | Server-defined (newest first) | Yes (`records_available=false`, `[]`) |
| `GET /api/v1/students/me/test-results/summary` | Bearer JWT | Yes | 100 records (server default) | Server-defined (newest first) | Yes (`records_available=false`, `[]`) |
| `GET /api/v1/students/me/notices?limit=5` | Bearer JWT | Yes | 1..20 (dashboard sends 5) | Pinned first, then newest | Yes (`items: []`) |
| `GET /api/v1/students/me/resources?limit=6` | Bearer JWT | Yes | 1..50 (dashboard sends 6) | Newest first | Yes (`items: []`) |

Notes:

- Identity: every endpoint accepts NO identity parameter; the student is
  resolved server-side from the JWT (`users.user_id → students.user_id`).
- Tenant: `assert_tenant_object` / server-resolved `institution_id` on every path; client-supplied `institution_id`/`student_id` values are ignored.
- Authorization: only `approved`, `is_active` students get data; pending students get the existing `STUDENT_NOT_APPROVED` failure surfaced as a section error.
- Read-only: only `GET` routes exist on `/students/me/*` (asserted by `test_only_get_is_registered_on_student_paths`).
- Performance: expected 6 requests, actual 6, duplicates 0 (verified by `StudentDashboardHardening.test.tsx`).

## 4. API Contracts

All response schemas are Pydantic `extra="forbid"` models — any internal
field in a payload is rejected by tests, not silently tolerated:

- `StudentAcademicProfile` (`schemas/student_profile.py`): every field optional (`student_number`, `register_number`, `university_roll_number`, `email`, institution/program/academic-year/semester names+codes, `approval_status`, `status`). No internal IDs by design.
- `StudentOwnAttendance` (`schemas/student_attendance.py`): server-computed `summary` (`records_available`, counts, `attendance_percentage: float | None`) + `records` (`date`/`status`/`notes`). Percentage is `None` when there are no rows — the authoritative attendance rule lives server-side.
- `StudentOwnResults` / `StudentOwnTestResults` (`schemas/student_results.py`): counts-only summaries (`records_available`, `total_results` — no invented aggregates) + per-record rows whose `letter_grade`, `percentage`, and course-code/name labels may be `None`.
- `StudentNoticeList` (`schemas/student_notices.py`): `items` + `total`; rows keep `notice_id` (stable list key, never rendered) and exclude `institution_id`, `created_by`, `is_active`, `is_published`, `updated_at`.
- `StudentResourceList` (`schemas/student_resources.py`): `items` + `total`; rows keep `resource_id` (stable list key, never rendered) and exclude all storage/pipeline/tenant internals (`storage_bucket`, `storage_object_key`, `file_checksum`, `document_id`, `document_version_id`, `institution_id`, `created_by_user_id`). No download URL is produced.

Frontend types in `types/student.ts` mirror these exactly; optional
fields are optional in the frontend types too — the UI never assumes a
field exists because it is currently displayed.

## 5. Partial Failure

Each section owns its own state, so one failing request cannot blank the
dashboard. `useStudentResource` isolates failures: only the failing
section transitions to `error` and renders an `ErrorBlock` with a fixed
user-safe message (e.g. "Unable to load results.") plus a "Try again"
button; all other sections keep their data. Verified by:

- `StudentDashboardHardening.test.tsx` — "keeps academic data visible when only test results fail".
- `StudentDashboardIntegration.test.tsx` — "one failing section keeps the dashboard usable".

The dashboard never becomes a full-page error screen for a section-level
failure. A 401 is the single exception: it raises the existing global
session-expiry notification (Phase 6.15.7) and the AuthProvider signs the
user out — this is intentional, not a partial-failure regression.

## 6. Retry Behavior

Every section error exposes a real `<button>` retry (`ErrorBlock` →
`onRetry={state.reload}`). `reload` re-runs ONLY that section's loader:

- It does not reload the application, navigate, or touch the session.
- It does not re-issue requests for sections that succeeded (each hook
  instance re-fetches only when its own token changes or its own
  `reload` is called).
- The generation guard in `useStudentResource` makes retries safe: a
  late response from a superseded attempt is discarded, so
  failure → retry → success and failure → retry → failure both leave
  the section consistent (tested: "retries only the failed section",
  "stays failed when retry also fails").
- No retry loop exists: retries are user-initiated only; there is no
  automatic backoff/requeue that could spin.

## 7. Loading States

Every section distinguishes `idle`, `loading`, `loaded (with data)`,
`loaded (empty)`, and `failed` via `SectionState.tsx`:

- Loading renders `LoadingBlock` (`role="status"`, polite announcement +
  spinner) — never a fabricated value.
- Empty renders `EmptyBlock` with neutral wording ("No attendance
  records are available yet."), never failure language.
- Failed renders `ErrorBlock` (`role="alert"`) with retry.
- No section renders `0`, `0%`, "No results", or "No notices" while
  loading. Attendance figures render only after the payload arrives with
  `records_available === true` and at least one record; otherwise the
  empty state is shown. Malformed numerics render as `—`
  (`formatPercent`/`formatNumber` guard with `Number.isFinite`), never `NaN`.

## 8. Optional Data

All identity/academic fields are optional and rendered through
`formatText` / `formatLabel` / `formatDate`, which collapse missing,
empty, non-string, and non-finite values to the em dash placeholder
(`NOT_PROVIDED = '—'`). The UI can never display `undefined`, `null`,
`NaN`, or `[object Object]`:

- Missing roll/register/number fields → `—`.
- Missing program/department/semester/year labels → `—`.
- `formatLabel` never invents a status vocabulary; it only normalises
  whitespace/underscores of a server-supplied string.
- No replacement data is invented anywhere. Tested by
  `StudentDashboardEdgeCases.test.tsx` ("degrades incomplete identity to
  placeholders", "renders malformed list payloads as empty states").

## 9. Academic Context

Backend is authoritative; the frontend has NO "current semester" logic —
it renders `current_semester_name` / `academic_year_name` exactly as the
backend resolves them:

- No active semester / no academic year → `—` placeholders (fields are
  optional in `StudentAcademicProfile`).
- Multiple historical academic records → the backend resolver selects
  the single current record; the UI renders only what is returned.
- Missing program / department / section → `—`.
- Newly approved student with no academic records → identity card and
  academic-context card render with placeholders; no errors, no
  fabricated "Semester 1".

## 10. Attendance

- No records → empty state; `attendance_percentage` is `None`
  server-side and the UI shows the empty state, never "0%".
- Zero / 100% attendance → rendered verbatim from
  `attendance_percentage` (backend-computed `round(present/total*100, 2)`).
- Partial / missing optional fields → `—` placeholders; counts render
  only when finite.
- Large record counts → bounded by the server limit (200, most recent
  day first); the records table scrolls horizontally intentionally
  (`overflow-x-auto` + `min-w-[28rem]`).
- Invalid backend percentage (non-finite/malformed) → rendered as `—`,
  never `NaN` (tested: "renders malformed percentage as placeholder,
  never NaN").
- Unauthorized / cross-tenant access → 403 surfaced as the section
  error; nothing renders. The frontend performs zero attendance
  arithmetic — every number is backend-computed.

## 11. Results

- No results → `EmptyBlock` ("No published results are available yet.").
- One / multiple results → rendered verbatim from the records array;
  summary shows only the server-provided count (`total_results`).
- Incomplete rows / missing grade / missing percentage → `—` via the
  safe formatters; no invented values.
- Multiple exam/test categories → academic results and test results are
  two independent sections/payloads, rendered from their own endpoints.
- Large result sets → bounded by the server limit (100 records each).
- The frontend never computes overall percentage, average, grade, or
  rank; summaries are counts-only per the locked schema.

## 12. Notices

- No notices / exactly one → `EmptyBlock` or a single row.
- Dashboard limit: 5 (server `DEFAULT_NOTICE_LIMIT = 5`, hard bounds
  1..20); the full Notices page requests up to 20.
- More than the limit → the server truncates; `total` reports the full
  count and the dashboard card shows the bounded slice only.
- Duplicate notice records → rendered one-to-one as stored; the
  frontend invents no deduplication business rules (documented in
  Section 16 and tested server-side by
  `test_duplicate_rows_project_one_to_one`).
- Unpublished / inactive / expired / cross-institution notices → never
  returned: publication + tenant filtering is server-side
  (`is_published`, `is_active`, `expires_at`, own `institution_id` only).
- Malformed optional fields → safe formatters; never raw rendering.
- The server remains authoritative; there is no client-side security
  filtering of notices.

## 13. Learning Resources

- No resources / exactly one → empty state or a single card.
- Dashboard limit: 6 (`DEFAULT_RESOURCE_LIMIT = 6`, bounds 1..50); the
  full Resources page requests up to 50.
- More than the limit → server truncates; `total` reports the full count.
- Duplicate resources → rendered one-to-one; no invented client dedup.
- Unknown/unsupported source types → rendered via `formatLabel` as-is;
  the excluded vocabulary (`notice`, `faq`) is enforced server-side so
  the dashboard never duplicates the Notices section or the assistant's
  inline FAQ answers.
- Missing metadata (description, effective dates) → `—` placeholders.
- Inaccessible / cross-tenant resources → only the student's OWN
  institution's `published` knowledge sources are ever returned
  (server-side).
- The dashboard never exposes storage keys, buckets, document/version
  IDs, private or signed URLs — none are projected by the schema.

## 14. Ordering and Limits

All ordering is server-defined and the frontend re-sorts nothing:

- Notices: pinned first, then newest (repository-level ordering);
  dashboard receives at most 5 (`limit=5`).
- Resources: newest first; dashboard receives at most 6 (`limit=6`).
- Attendance: most recent day first; at most 200 records.
- Results / test results: server-defined order; at most 100 records each.
- React lists use stable keys (`notice_id` / `resource_id` UUIDs for
  notices/resources; composite `date-index` keys for attendance rows)
  so server order is preserved and keys never collide.
- No client-side sorting exists that could change server semantics.

## 15. Duplicate Records

Backend duplicates are projected one-to-one — the frontend invents no
deduplication business rules to hide a data-quality problem (that is an
admin data-hygiene concern, documented here instead). The frontend does
guarantee that duplicates cannot break the UI:

- List keys are stable UUIDs (`notice_id`, `resource_id`) or composite
  `date-index` keys, so duplicate rows can never produce duplicate
  React keys or broken lists.
- Retries cannot duplicate records: `reload` replaces the section state
  wholesale (`setState`), it never appends.
- Request races cannot duplicate records: the generation guard discards
  stale responses entirely.
- Server-side behavior verified by `test_duplicate_rows_project_one_to_one`.

## 16. Request Race Conditions

`useStudentResource` is generation-guarded (`generationRef`): every load
increments the generation, and a resolving promise applies its state only
if its generation is still current. Therefore:

- Navigating away cannot update unmounted/stale state incorrectly
  (unmount drops the consumer; the guard drops stale writers).
- A superseded request (token change, retry) can never overwrite newer
  data with older data.
- No request-cancellation framework, no state-management library, and
  no speculative caching were introduced — the guard reuses the
  existing Phase 6.16 primitive unchanged in shape.

## 17. Refresh Behavior

Phase 6.15 session lifecycle is reused verbatim:

- On browser refresh, `AuthProvider` restores the session from
  localStorage and resolves the authenticated state BEFORE the student
  shell renders; `StudentShell` renders only with a valid access token,
  so the dashboard never flashes stale or another user's data.
- Sections stay `idle` (no request) until a valid token exists.
- The 401 → `notifySessionExpired` → sign-out path is unchanged.
- No duplicate requests on refresh: six hooks fire exactly once per
  mount, and remounts only occur when the shell actually re-renders
  (verified by the request-count test: 6 requests, 0 duplicates).

## 18. Navigation

All seven views verified (`studentNavigation.test.ts`,
`StudentShellNav.test.tsx`): Dashboard, Attendance, Results, Notices,
Learning Resources, AI Assistant, Profile.

- Each preserves authentication (inside `StudentShell`, which renders
  only when authenticated), the student role, and tenant context.
- Active navigation state tracks the current view; direct browser
  navigation to student routes resolves through the same guarded shell.
- No privileged route is exposed: the student experience contains no
  admin/faculty links, and all data paths are `/students/me/*`.
- Truncation-safe nav labels (`min-w-0`/`truncate`) keep the bar
  stable with long names.

## 19. Accessibility

- Heading hierarchy: one `<h1>` (view title) + one `<h2>` per section
  via `SectionCard` + `aria-labelledby` with stable heading IDs.
- Landmarks: navigation is a real `<nav>`; each section is a `<section>`.
- Keyboard: all interactive controls are native `<button>`/`<a>`
  elements with visible `focus:ring-2` focus styles; the full dashboard
  is operable keyboard-only (Tab through nav → section actions → retry
  buttons → assistant CTA).
- Screen-reader labels: tables have `<caption>` (`sr-only`), status
  columns are text (colour is decorative only), figures use `<dl>`
  definition lists, loading uses `role="status"`, errors use
  `role="alert"`.
- Button/link names are explicit text ("View all attendance", "Try
  again", "Open AI Assistant"); no icon-only controls, no ARIA added
  beyond the standard roles above.

## 20. Responsive Behavior

- `min-w-0` + `overflow-x-clip` on the dashboard root prevent
  horizontal page overflow from long student/institution names, notice
  titles, and resource titles; `break-words` on headings/body text.
- Mobile: single-column sections; nav labels truncate; tables scroll
  horizontally inside their own `overflow-x-auto` container only.
- Tablet (`lg` breakpoint): attendance/results become a two-column grid.
- Desktop: wide viewports keep max content width; wide tables scroll
  intentionally.
- Verified rendering in `StudentDashboard.test.tsx`,
  `StudentShellNav.test.tsx`, and the hardening/edge-case suites;
  no clipped controls or overlapping cards observed.

## 21. Data Minimization

Reviewed every dashboard response against consumption:

- No `auth_user_id`, internal database IDs, or institution UUIDs are
  projected anywhere (schemas are `extra="forbid"` and the HTTP-level
  test `test_payloads_never_leak_internal_fields_over_http` asserts it
  end-to-end).
- `notice_id` / `resource_id` UUIDs are retained as the stable list-key
  contract (matching the locked Phase 6.11 notification contract) and
  are never rendered by the UI (asserted by frontend tests).
- Storage internals (`storage_bucket`, `storage_object_key`,
  `file_checksum`, `document_id`, `document_version_id`) and admin
  workflow fields (`is_active`, `is_published`, `created_by`,
  `updated_at`) are excluded by design.
- Backend contract-hardening candidates found: none — every currently
  projected field is consumed or serves as the documented list key.

## 22. Backend Contract Verification

New file `backend/tests/test_student_dashboard_hardening_phase_6_16_1.py`
(9 tests, hermetic mock-Supabase style consistent with the existing
suite):

- `test_dashboard_defaults_and_bounds_are_pinned` — notices 5/20, resources 6/50 pinned.
- `test_tenant_filter_is_mandatory_on_both_repository_queries` — tenant filter present on both list queries.
- `test_projections_exclude_unsafe_columns` — select-projections contain no internal columns.
- `test_service_limit_validation_stays_bounded` — 0, 21, 51 and non-int limits rejected with 422 `INVALID_FILTER`.
- `test_duplicate_rows_project_one_to_one` — duplicate stored rows project without invented dedup.
- `test_response_models_reject_internal_fields` — `extra="forbid"` rejects injected internal fields.
- `test_cross_tenant_profile_is_denied_with_403` — cross-tenant denial via `assert_tenant_object`.
- `test_payloads_never_leak_internal_fields_over_http` — HTTP-level minimization over all `/students/me/*` payloads.
- `test_only_get_is_registered_on_student_paths` — read-only enforcement.

No backend behavior change was required — no concrete defect found.

## 23. Frontend Contract Verification

New files (Vitest + Testing Library, user-visible-behavior oriented):

- `StudentDashboardHardening.test.tsx` — request count/limits (6
  requests, `limit=5`/`limit=6`), server-ordered rendering, retry of
  only the failed section, partial failure isolation, retry-failure
  stability.
- `StudentDashboardEdgeCases.test.tsx` — incomplete identity
  placeholders, empty attendance (never a fabricated zero percent),
  malformed percentage → placeholder (never NaN), malformed list
  payloads → empty states, duplicate rows rendered without invented
  dedup, malformed result rows never rendered as `undefined`/object text.
- `StudentDashboardIntegration.test.tsx` — full authenticated journey
  (identity → academic context → attendance → results → notices →
  resources → assistant navigation) and one-failing-section usability.
- Existing suites extended/kept green: `studentApi.test.ts`,
  `StudentDashboard.test.tsx`, `StudentDashboardStates.test.tsx`,
  `studentNavigation.test.ts`, `StudentShellNav.test.tsx`.

## 24. Integration Testing

`StudentDashboardIntegration.test.tsx` covers the required scenario with
a mocked `studentApi` boundary:

- authenticated student → dashboard load → identity → academic context
  → attendance → results (academic + test) → notices → resources →
  "Open AI Assistant" navigation, all with realistic payloads.
- The same suite verifies the dashboard stays usable when one
  independent section fails (its error + retry renders; other sections
  keep their data).

## 25. Performance Verification

- Expected requests on initial dashboard load: 6.
- Actual requests: 6 (one per `useStudentResource` instance, fired
  concurrently).
- Duplicate requests: 0 — each hook fires exactly once per mount; the
  fetch mock in the test harness counts every call, and the
  request-count assertion passes.
- No caching layer or speculative prefetch was introduced.

## 26. Issues Found

1. Incomplete identity records could render raw `undefined`/`null`
   values through ad-hoc string interpolation in
   `StudentIdentityCard`/`AcademicContextCard`.
2. Non-string or empty status/label values (malformed backend rows)
   could render as `undefined`, `null`, `NaN`, or `[object Object]`.
3. Malformed/non-finite numeric payloads (percentage, marks) could
   render as `NaN` or `%`.
4. Section heading rows and the dashboard root lacked `min-w-0`
   guards, allowing long names/titles to push the layout horizontally
   on narrow viewports.
5. Malformed list payloads (non-array `records`/`items`) could crash a
   panel instead of degrading to an empty state.

## 27. Fixes Applied

1. `studentFormat.ts` hardened: `formatText` (safe rendering for any
   payload type), `formatPercent`/`formatNumber` (`Number.isFinite`
   guards), `formatLabel` (string-only, never invents vocabulary),
   `isDisplayableNumber` helper.
2. `StudentIdentityCard` / `AcademicContextCard` route every value
   through the safe formatters with `NOT_PROVIDED` placeholders.
3. `AttendancePanel`: explicit loading/empty/error split, empty state
   when `records_available` is not `true` or records are empty (never a
   fabricated zero percent), safe count/percentage formatting, safe row
   keys, table `caption`, truncated cells.
4. `ResultsPanel` / `NoticesPanel` / `ResourcesPanel`: null/shape-safe
   rendering, `Array.isArray` guards on list payloads, stable UUID list
   keys, safe label/date/score formatting.
5. `SectionCard` heading row and dashboard root: `min-w-0`,
   `flex-wrap`, `break-words`, `overflow-x-clip` — no horizontal page
   overflow, no clipped section actions.
6. `StudentShell`: truncation-safe nav labels.
7. No backend behavior change; no contract change; no new dependencies.

## 28. Accepted Limitations

- Duplicate backend rows are rendered as stored — deduplication is an
  admin data-hygiene concern, deliberately out of scope.
- No automatic retry/backoff: retries are user-initiated only (by
  design, to avoid uncontrolled request loops).
- Attendance has no course/section label columns (the stored rows carry
  only foreign keys; no verified label helper exists for this path —
  documented in the schema, not invented).
- Notice/resource pagination beyond the max limits (20/50) is not
  implemented anywhere in the product; the dashboard uses bounded
  slices with server-provided `total` counts.
- Accessibility/responsive auditing used static analysis + component
  tests; no automated axe or screen-reader run is part of the suite.

## 29. Git Scope

Changed / added files (all in the working tree, NO commit created):

- Modified: `frontend/src/features/student/` — `AcademicContextCard.tsx`,
  `AttendancePanel.tsx`, `NoticesPanel.tsx`, `ResourcesPanel.tsx`,
  `ResultsPanel.tsx`, `SectionState.tsx`, `StudentDashboard.tsx`,
  `StudentIdentityCard.tsx`, `StudentShell.tsx`, `studentFormat.ts`
- Added: `frontend/src/features/student/StudentDashboardHardening.test.tsx`,
  `StudentDashboardEdgeCases.test.tsx`, `StudentDashboardIntegration.test.tsx`
- Added: `backend/tests/test_student_dashboard_hardening_phase_6_16_1.py`
- Added: `PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING.md` (this file)

Unrelated files changed: none. Branch: `main`; Phase 6.16 baseline
commit `ea727bc` untouched.

## 30. Phase Completion Status

COMPLETE — verified 2026-09-21 (full report in the phase chat; summary):

- Frontend: Vitest suite fully passing; TypeScript (`tsc -b`) clean;
  production build succeeded.
- Backend: pytest full suite passing (0 failures); remaining warnings
  are pre-existing third-party deprecations.
- Resilience, data validation, security, accessibility, responsive, and
  performance checks: all verified (Sections 5–25).
- Git scope as documented in Section 29; no automatic commit created.

STOP: Phase 6.16.1 complete. Phase 6.16.2 and Phase 6.17 NOT started.






