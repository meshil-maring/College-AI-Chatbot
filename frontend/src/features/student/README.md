# Student self-service feature

Keep pages, panels, and tests with their owning student workflow. The feature
root contains this guide and domain folders. Import modules directly from their
owning folder; update callers and mock targets together when moving code.

| Folder         | Responsibility and entry points                                                         |
| -------------- | --------------------------------------------------------------------------------------- |
| `workspace/`   | `StudentShell.tsx`, navigation, account access, and session-expiry tests                |
| `dashboard/`   | `StudentDashboard.tsx`, summary composition, and dashboard tests                        |
| `attendance/`  | `AttendanceDetail.tsx`, dashboard panel, filters, records, and tests                    |
| `results/`     | `ResultsDetail.tsx`, dashboard panel, record tables, and tests                          |
| `profile/`     | `ProfilePage.tsx`, identity card, and profile tests                                     |
| `notices/`     | `NoticesPage.tsx`, dashboard panel, and notice tests                                    |
| `resources/`   | `ResourcesPage.tsx`, dashboard panel, and resource tests                                |
| `shared/`      | Resource hook, access-denial context, section UI, formatting, and academic context card |
| `integration/` | Academic detail and information journeys, navigation, and error-isolation tests         |
| `__tests__/`   | Shared student data fixtures used by student and application tests                      |

The workspace composes the domain pages directly. Dashboard panels reuse their
domain's rendering, and the profile's academic context card is shared with the
dashboard and academic detail pages. API clients remain in
`src/services/students/`; contracts remain in `src/types/student.ts`.
Shared staff and faculty student-management UI belongs in `features/students/`.

Keep tests beside their owning page or workflow. Shared mock setup belongs in
that workflow's `__tests__/` folder and must be imported before the component
under test. These fixture folders are excluded from the production TypeScript
build. Keep assertions in test files.

Preserve approval and inactive-account handling, server-authoritative permissions,
session-expiry behavior, request limits, and the read-only student contracts.
Keep the resource hook's identity and query scope, error reporting, retry
behavior, and cache lifetime intact when extracting code.

Keep every folder within 15 direct maintained files and each code file within
250 physical lines. `npm run check:structure` checks both limits throughout this
feature. Group further by responsibility before reaching either limit.
