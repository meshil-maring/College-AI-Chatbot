# Faculty feature

Keep faculty screens, state, helpers, and tests with their owning workflow.
The faculty root contains this guide and workflow folders. Import modules from
their owning folder and update callers and mock paths together when moving code.

| Folder          | Responsibility and entry points                                             |
| --------------- | --------------------------------------------------------------------------- |
| `workspace/`    | `FacultyShell.tsx`, routes, navigation, and coming-soon screens             |
| `dashboard/`    | Faculty dashboard and its tests                                             |
| `profile/`      | Faculty profile and identity card                                           |
| `assignments/`  | Teaching assignments, responsibilities, validity, and faculty context       |
| `attendance/`   | Attendance screen and workflow tests                                        |
| `students/`     | Student workspace, navigation, academic scope, and registration history     |
| `examinations/` | Assessment workflow, test creation, marks editing, import review, and tests |

Attendance groups its implementation further into:

- `state/`: queries, workspace state, actions, and local types.
- `dialogs/`: marking, upload, profile, and shared dialog UI.
- `roster/`: student roster, tables, recorded views, and history.
- `upload/`: file selection, validation, and import review stages.
- `shared/`: UI primitives and presentation helpers.

The students workflow keeps directory components in `roster/` and registration
forms, academic selection, and spreadsheet helpers in `registration/`.

Keep tests beside their owning workflow. Shared mock setup belongs in that
workflow's `__tests__/` folder and must be imported before the component under
test. Assessment UI belongs in `examinations/`; test files use `.test.ts` or
`.test.tsx` names rather than an ambiguous `tests/` component folder.

Keep every folder within 15 direct maintained files and each code file within
250 physical lines. `npm run check:structure` checks both limits throughout this
feature. Group further by responsibility before reaching either limit.

API clients stay in `src/services/faculty/`, `src/services/students/`, or the
owning admin service module. Reuse shared Students UI and workspace adapters
without duplicating registration or approval contracts.

Preserve identity and scope keys, server-authoritative permissions, assignment
validity, request cancellation, and query invalidation when moving modules.
Route changes must preserve direct links, section query parameters, and browser
Back/Forward behavior. Keep authorization decisions on the backend.
