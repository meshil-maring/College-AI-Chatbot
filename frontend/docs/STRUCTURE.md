# Frontend structure

The app uses React, TypeScript, Vite, and TanStack Query. Files are grouped by
feature, with state, UI, transport, and API contracts kept in separate modules.
Every code, test, and stylesheet file is limited to 250 physical lines.

## Before adding files or growing modules

Follow the [shared project rules](../../AGENTS.md) before creating a file. Inspect
the existing structure and nearby implementation, reuse the appropriate owning
module when possible, and place new code inside the existing feature boundaries.

Keep each folder at or below 15 directly contained, project-maintained files.
Count all maintained file types, including tests, docs, and configuration; apply
the limit separately to every subfolder. Before adding a sixteenth file, or
adding anything to a folder already above the limit, group related files into
descriptive subfolders such as a workflow's components, state, or test fixtures.
Choose groups that fit the actual feature, rather than creating empty folders
or numbered buckets.

The 250-line limit includes imports, comments, and blank lines. Split growing
files by responsibility before exceeding it, preserving readable formatting.
Update imports, public exports, tests, and guide links together when moving code.
Generated dependencies, build output, caches, lockfiles, and archived evidence
are excluded as described in the shared rules.

## Folder hygiene

Keep the frontend root for package and tool configuration, `index.html`,
`AGENTS.md`, and the standard project folders. Put frontend guides in `docs/`.
Keep local build and test logs in the repository-level `logs/frontend/` folder,
which is ignored by Git; create it before redirecting command output. Build
output belongs in `dist/`, and installed dependencies belong in `node_modules/`.

## Start here

| Location                                   | Responsibility                                        |
| ------------------------------------------ | ----------------------------------------------------- |
| `src/main.tsx`                             | React and provider bootstrap                          |
| `src/App.tsx`                              | Compose public routes and authenticated route gates   |
| `src/app/routes.ts`                        | Parse paths, institution codes, and invitation tokens |
| `src/app/RouteGates.tsx`                   | Choose the appropriate access and login screen        |
| `src/app/AuthenticatedExperience.tsx`      | Select the role workspace using server identity       |
| `src/features/`                            | Feature screens, hooks, and UI components             |
| `src/services/`                            | HTTP clients and session-expiry notifications         |
| `src/types/`                               | Typed backend request and response contracts          |
| `src/hooks/`, `src/lib/`, `src/providers/` | Shared query, navigation, and provider infrastructure |
| `src/test/`, feature `__tests__/` folders  | Shared test infrastructure, fixtures, and mock setup  |

## Feature ownership

| Location                                                    | What to read or change there                                                       |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `features/auth/session/`                                    | Auth context, browser storage, restore, login/logout, renewal, cross-tab events    |
| `features/auth/login/`                                      | Sign-in UI, audience selection, and validation                                     |
| `features/auth/password/`                                   | Shared password fields, password change, recovery, and reset                       |
| `features/auth/registration/`                               | Institution lookup, registration state, fields, success screen                     |
| `features/auth/access/`                                     | Permission helpers, permissions hook, and generated RBAC reference                 |
| `features/adminInvitation/`                                 | Invitation acceptance hook and form                                                |
| `features/students/subject-assignment/` | Missing subject memberships, assignment actions, and workflow tests |
| `features/academic-packages/` | Shared curriculum/class setup, fixed package assignment, requests, decisions, and history |
| `features/admin/students/import/`                           | Spreadsheet parsing, validation, CSV reports, import state, and workflow stages    |
| `features/admin/students/directory/`                        | Student directory filters, pagination, statistics, and export state                |
| `features/admin/documents/`                                 | Document UI and request lifecycle                                                  |
| `features/faculty/workspace/`                               | Faculty shell, routes, navigation, and coming-soon screens                         |
| `features/faculty/dashboard/`, `features/faculty/profile/`  | Faculty dashboard, profile, and identity card                                      |
| `features/faculty/assignments/`                             | Teaching assignments, responsibilities, validity, and faculty context              |
| `features/faculty/attendance/`                              | Attendance state, actions, roster, dialogs, upload, validation, review             |
| `features/faculty/students/`                                | Student workspace, section roster state, table, toolbar, and shared UI             |
| `features/faculty/examinations/`                            | Assessment creation, marks editing, import review, and workflow tests              |
| `features/student/workspace/`                               | Student shell, navigation, account access, and session-expiry tests                |
| `features/student/dashboard/`                               | Dashboard overview, summary composition, and dashboard tests                       |
| `features/student/attendance/`, `features/student/results/` | Academic pages, summary panels, filters, record tables, and tests                  |
| `features/student/profile/`                                 | Read-only profile page, identity card, and tests                                   |
| `features/student/notices/`, `features/student/resources/`  | Information pages, dashboard panels, and tests                                     |
| `features/student/shared/`                                  | Resource hook, access-denial context, section UI, formatting, and academic context |
| `features/student/integration/`                             | Cross-page journeys, navigation, and error-isolation tests                         |
| `features/publicChat/storage/`                              | Stored conversation validation, migration, and persistence                         |
| `features/superAdmin/roster/`                               | Admin roster state, invitation notice, table, and confirmations                    |
| `features/superAdmin/institutions/`                         | Institution list, creation, detail state, configuration, branding, and assignment  |

See [the admin guide](../src/features/admin/README.md) for the other admin sections.
See [the auth guide](../src/features/auth/README.md) for auth workflow entry points
and the RBAC snapshot generation command.
See [the faculty guide](../src/features/faculty/README.md) for workflow entry
points and attendance and student subfolder ownership.
See [the student guide](../src/features/student/README.md) for self-service page
entry points, shared resource state, and test ownership.
The remaining feature folders retain their existing responsibilities.

## Public import boundaries

Services and their tests live inside their owning domain. Import clients through
the domain paths below; see [the services guide](../src/services/README.md) for
the complete folder map. Existing exported contracts remain available after the
move, and callers and mocks use the new paths. Type facades retain their paths.

| Entry                                          | Implementation folders                                                                       |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `services/admin/adminApi.ts`                   | `services/admin/`: transport, academics, identity, knowledge, students, faculty, memberships |
| `services/academics/academicPackagesApi.ts`     | Cross-role authenticated academic package catalogue and typed commands |
| `services/auth/auth.ts`                        | `services/auth/`: endpoints, errors, transport, session operations                           |
| `services/registration/registration.ts`        | `services/registration/`: errors and public registration client                              |
| `services/platform/platformInstitutionsApi.ts` | `services/platform/`: transport, institutions, invitations, audit                            |
| `types/admin.ts`                               | `types/admin/`: knowledge, students, dashboard, memberships                                  |
| `types/platform.ts`                            | `types/platform/`: institutions, invitations, roster/audit                                   |

Feature code can use those facades. Implementation modules should import their
siblings directly to avoid a dependency back through the facade. Transport and
contract modules must not depend on feature components.

## Styles and tests

`features/students/students.css` and `features/admin/adminWorkspace.css` are
ordered stylesheet entry points. Their `styles/` folders group rules by purpose.
Keep the import order: later responsive and workflow rules intentionally override
earlier rules.

Large test suites are split into related scenario files using shared support
modules in `__tests__/`. Those support modules register the same mocks and hooks
for each test file. Import them first; mutable fixture values must be changed
through their exported helpers. Keep assertions in test files.

## Validation

Run these commands from `frontend`:

```sh
npm run check:structure
npm run build
npm test
```

`npm run check` runs all three. The structure check includes tests, fixtures,
stylesheets, config code, and scripts. `npx prettier --write <path>` formats a particular file or folder.
`npm run format` formats the frontend; run the structure check after formatting.
The validator also checks the 15-file limit throughout `src/services`,
`src/features/auth`, `src/features/faculty`, and `src/features/student`. Review
direct file counts in other affected folders against the same shared rule.
