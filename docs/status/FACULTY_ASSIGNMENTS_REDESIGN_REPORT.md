# Faculty Assignments redesign

Date: 9 October 2026.

The Faculty Assignments page now follows the supplied reference: a compact academic header, three data-driven summary cards, separate teaching creation and record panels, and a separate responsibility workspace. The implementation uses the existing Tailwind utilities, Lucide icons, API clients, query cache, and management endpoints.

## Files changed

| File | Purpose |
| --- | --- |
| `frontend/src/features/admin/FacultyAssignmentManager.tsx` | Page header, summary cards, teaching form, search, refresh, desktop table, mobile cards, and existing management actions. |
| `frontend/src/features/admin/FacultyResponsibilityManager.tsx` | Separate responsibility form and record cards; shared existing management query; selection, validation, loading, and error handling. |
| `frontend/src/features/admin/TeachingValidityEditor.tsx` | Responsive validity editor with validation, cancel, duplicate-submit protection, and safe failure feedback. |
| `frontend/src/features/admin/facultyAssignmentUi.tsx` | Page-specific visual utilities, feedback, status badges, and validity presentation. |
| `frontend/src/features/admin/FacultyAssignmentManager.test.tsx` | Existing tests retained and expanded for the redesigned workflows. |
| `frontend/src/features/admin/FacultyResponsibilityManager.test.tsx` | Existing tests retained and expanded for responsibility management. |
| `frontend/src/features/admin/facultyAssignmentUi.test.ts` | Start-inclusive/end-exclusive status boundaries, legacy timestamps, revocation, and unavailable validity. |
| `frontend/src/features/admin/AdminShell.tsx` | One view-specific condition lets this page supply its own header, preventing a duplicate heading. Navigation and all other views are unchanged. |
| `frontend/src/features/admin/AdminShell.test.tsx` | Two Faculty Assignments empty-state expectations updated; caching assertions retained; one-heading assertion added. |
| `docs/status/FACULTY_ASSIGNMENTS_REDESIGN_REPORT.md` | Implementation, verification, and backend investigation report. |

## Visual and interaction changes

- Navy surfaces, subtle borders, rounded controls, green primary actions, and blue/purple/green icon tiles match the reference structure.
- Desktop forms use two columns. The information panel and responsibility records occupy separate columns when space permits. Smaller screens stack fields and render teaching records as cards.
- Teaching records display faculty names/emails, section codes/names, localized validity periods, status text, and compact management/revoke actions. Responsibility records retain server-supplied scope labels and states.
- Search filters only the already-loaded assignment response by faculty name, email, or section. It introduces no additional queries.
- Required and invalid date fields receive nearby, announced validation messages. Controls have visible keyboard focus, native accessible selects, dark date pickers, and action heights of at least 40 pixels.
- Mutation guards prevent duplicate submissions; failed requests preserve entries. Successful mutations refresh the existing queries. Clear/cancel controls are explicit, and switching faculty closes the previous responsibility editor.
- Failed reads retain previously loaded records with a refresh-failed label, show an error and retry, and disable mutations until a successful read. Initial failure is distinguished from a successful empty response.

## Data and security preserved

Summary values come from the existing APIs. Active teaching assignments use the authoritative enabled/revocation fields and UTC validity timestamps, following the backend's half-open validity rule. Distinct faculty are counted from those active records. Missing validity makes the affected count/status unavailable. Responsibility totals use the management response's `effective_active` and `state`, across the institution rather than only the selected faculty.

No backend API, endpoint, schema, migration, audit behavior, or permission model was changed. Requests still use the existing token-bound clients and queries, and mutations supply only the existing contract fields. The backend remains responsible for authorization, tenant isolation, validity, exclusive appointments, and revocation. Existing HOD department scope, explicit Coordinator scope, Class In-Charge limits, Faculty self-management denial, and University Admin institution scope remain in place.

## HTTP 500 investigation

The exact failure shown in the supplied screenshot was **not reproduced**, so its root cause has not been established and no backend fix is claimed.

The repository's earlier `FACULTY_LOGIN_SCHEMA_FIX_REPORT.md` records a distinct, diagnosed failure: PostgREST `PGRST205` for missing `public.responsibility_definitions`. The current backend already converts recognized missing faculty tables, relationships, columns, and functions into `503 FACULTY_SCHEMA_UNAVAILABLE`, logs the required migration, and leaves unrelated failures unsuppressed.

Read-only checks against the configured database now succeeded for:

- Teaching assignment validity/revocation columns.
- Responsibility definitions and the nested responsibility-permission relationship.
- Responsibility validity/revocation columns.
- The full assignment-list service, responsibility scopes, definition service, and responsibility-list service for one existing institution.

Thus the earlier missing-schema condition is absent in the database checked during this run. These checks do not establish the cause of a failure from another deployment, institution, or backend process. The screenshot's request path and corresponding server diagnostic are needed to identify any continuing HTTP 500.

The page now distinguishes permission/session errors, unavailable schema, network failures, successful empty data, and unexpected server failures. It does not convert failed requests into empty arrays, render raw server diagnostics, or claim successful mutations after errors. Existing backend diagnostic logging is unchanged.

## Verification

| Check | Result |
| --- | --- |
| Faculty Assignments, responsibilities, status, and AdminShell integration tests | **53 passed** across 4 files; 42 page-focused cases plus 11 shell integration cases. |
| Full frontend suite | **686 passed** across 75 files. |
| TypeScript | `npx.cmd tsc -b` passed. |
| Production build | `npm.cmd run build` passed. Vite reports the application's main bundle above its 500 kB warning threshold. |
| Backend schema/authorization regression | **164 passed** using `test_admin_faculty_schema.py`, `test_faculty_responsibilities.py`, and `test_phase_8_1_authorization.py`. One dependency deprecation warning. |
| Browser rendering | Chromium checks passed at 320, 390, 768, 1024, 1312, and 1440 pixels: no horizontal overflow, controls within the viewport, and action heights at least 40 pixels. |
| Browser interactions | Search/clear and teaching-editor validation/cancel passed; no runtime page errors. The desktop table and smaller-screen cards expose exactly one visible set of management actions. |
| Static checks | `git diff --check` passed. No frontend lint command or ESLint configuration is present; strict TypeScript is the configured source static check. |

Frontend logs are retained locally as `frontend/faculty-assignments-focused-tests.log`, `frontend/faculty-assignments-full-tests.log`, `frontend/faculty-assignments-typescript.log`, and `frontend/faculty-assignments-build.log`. The temporary browser harness used only intercepted test responses, was removed after verification, and is absent from the production application. Screenshots are in the system temporary directory.

## Remaining limitations

- Live reads were verified; authenticated live creation, update, and revocation were not performed against institutional records. Their frontend workflows and backend security/error contracts were verified with automated tests. The page is not claimed to have completed a live end-to-end mutation test.
- The screenshot's specific HTTP 500 remains undiagnosed without a reproducible failing request or server diagnostic.
- The assignment endpoint omits revoked teaching records by design. The UI does not invent additional history; responsibility history remains visible when supplied by its existing API.
- Production build size optimization is outside this page-only redesign.
