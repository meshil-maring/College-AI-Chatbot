# Frontend structure

The app uses React, TypeScript, Vite and TanStack Query. State belongs in feature
hooks, rendering in focused components, transport in `services/` and contracts in
`types/`. Follow the [shared rules](../../AGENTS.md) before creating or moving files.

Keep every maintained code, test, stylesheet and script within 250 physical lines
and each folder within 15 directly contained maintained files. Inspect nearby
implementations first; reuse ownership boundaries and avoid forwarding modules.
Dependencies, generated output and local verification logs are excluded from
maintenance limits. Logs belong in repository-level `logs/frontend/`.

Follow the [design system](DESIGN_SYSTEM.md) for colors, typography, spacing,
component states and responsive layouts when creating or updating UI.

Follow the [server-state architecture](SERVER_STATE.md) for consistent TanStack Query
ownership, feature query modules, identity boundaries, mutations and data states.
It includes TypeScript recipes and an adoption checklist for new and migrated pages.

| Location                                   | Responsibility                                                              |
| ------------------------------------------ | --------------------------------------------------------------------------- |
| `src/main.tsx`, `src/App.tsx`              | Bootstrap and public/authenticated route composition                        |
| `src/app/`                                 | Path parsing, authentication gates and identity-scoped workspaces           |
| `src/styles/`                              | Shared design tokens, Tailwind theme, base controls and UI primitives       |
| `src/features/workspace/`                  | Common role workspace frame, page header and responsive shell styles        |
| `src/features/learning-resources/`         | Shared admin/faculty/staff library, audience/upload drafts and admin review |
| `src/features/auth/`                       | Session, sign-in, password, registration and server-grant helpers           |
| `src/features/admin/`                      | Institution account administration, approvals and knowledge management      |
| `src/features/staff/`                      | Staff identity, student account approvals and chat                          |
| `src/features/faculty/`                    | Faculty profile, existing information placeholders and chat                 |
| `src/features/student/`                    | Identity/approval gate, notices, resources and chat                         |
| `src/features/students/`                   | Shared account-approval UI and retained inactive roster source              |
| `src/features/superAdmin/`                 | Institution and administrator lifecycle                                     |
| `src/features/publicChat/`                 | Institution public chat and history storage                                 |
| `src/services/`                            | Domain API clients and session-expiry events                                |
| `src/types/`                               | Backend request/response contracts                                          |
| `src/hooks/`, `src/lib/`, `src/providers/` | Shared query, navigation and providers                                      |
| `src/test/`, workflow `__tests__/`         | Test setup and fixtures                                                     |

See the [admin](../src/features/admin/README.md),
[faculty](../src/features/faculty/README.md),
[student](../src/features/student/README.md),
[auth](../src/features/auth/README.md) and
[services](../src/services/README.md) guides for ownership. Feature consumers may
use domain service/type facades; implementation modules import siblings directly.
Preserve public import contracts, mock paths, identity keys, cancellation and
server-authoritative permissions when extracting code. Keep CSS import order.

The [public chat guide](../src/features/publicChat/README.md) owns browser-local
history, guarded anonymous requests and its focused `state/` and `recovery/` modules.

## Retained inactive source

The active Academic Setup overview lives in `academic-setup/overview/`, with
feature styles in `academic-setup/styles/`. It represents the eleven approved
entities without changing the existing service contract. See the
[design guide](ACADEMIC_SETUP_DESIGN.md) for the entity mapping and integration boundaries.
`academic-setup/navigation/` owns the setup journey, next-step guidance, direct
semester-subject/enrollment destinations and responsive navigation styles. Administrator
view/query parsing and browser history live in `features/admin/navigation/`.
Curriculum and calendar tabs share the workspace destination; navigation focuses
page headings while preserving keyboard focus when moving between tabs. Their
shared visibility hook keeps the active tab in view without scrolling the page.
The dedicated Departments page, drawer, state hooks and adjacent tests live in
`academic-setup/departments/`, with its own scoped `styles/` folder. It reuses
the existing department/program contracts and transport without remapping other
academic entities.

Academic Setup's shared `deletion/` owns department, program, academic-year,
dated-semester and class-section delete confirmation, eligibility and guarded
mutations. Calendar's `useCalendarDeletion.ts` coordinates its two record types.
Read-only users cannot open deletion; current periods and known links block
confirmation. The database checks all FK consumers, including inactive records
and student assignments, and audits deletion atomically. Deploy the additive
deletion migrations before using these DELETE actions.

The dedicated Programs page lives in `academic-setup/programs/`, with focused
form controls, scoped styles and adjacent tests. It uses the existing program
transport and immutable department relationship. Department and program drawers
share modal focus/scroll behavior with Learning Resources through
`features/workspace/useWorkspaceDialog.ts`.

The Academic Calendar page lives in `academic-setup/calendar/`. It owns year and
dated-semester views, filters, summaries, dates and timeline. Its `editor/` folder
owns accessible drawers, validation and checkpointed year/semester saves;
`styles/` and `__tests__/` keep its presentation and regression coverage local.
It uses the existing academic-year and semester contracts and identity-scoped
catalogue query. Dated semesters remain separate from proposed program stages.

The Subjects page lives in `academic-setup/subjects/`, with local `forms/`,
`styles/` and `__tests__/` folders. It manages reusable teaching courses through
the existing API. Semester and type displays/filters use institution-scoped
program-course assignments; subject saves retain the immutable department and
nullable credits/hours without adding curriculum relationships.

The Curriculum screen lives in `academic-setup/curriculum/`. Its `versioning/`
workflow manages stored drafts, publication, mapping structure and history.
Its `semester-plan/` view groups compulsory subjects, optional subjects and choice
groups by numeric program semester. Subject drawers and choice forms retain the
selected curriculum and semester. Publication reviews saved subjects and choices,
and waits for open choice drafts to be saved or cancelled. Missing semesters link to their setup page;
published and archived plans stay read-only. It reuses the existing structure
catalogue and write hooks without changing storage or API contracts.
Existing program-course mappings remain a separate tab, with dated-term groups
in `detail/` and mapping drawers in `editor/`. Shared course-type labels live in
`academic-setup/forms/academicCourseTypes.ts` and also serve Subjects.

Curriculum's `choices/` owns complete subject option groups embedded in each
semester card. There is no separate Subject Options tab or sidebar item; old
`curriculum-options` links resolve to `curriculum-subjects`. Academic Setup's
`registration/` owns administrator section assignment, registration queries and
scoped styles. These use the separate additive semester-registration API.
The option form explains missing entries on Save and keeps its draft while subjects
are added or edited in the same semester. Compulsory subjects are excluded from
option selections. Choice reads/writes reuse the identity-scoped registration
query factory and mutation guards. Published and archived groups remain read-only.

The Batches screen lives in `academic-setup/batches/`, with focused `editor/`,
`styles/` and `__tests__/` folders. Its `cohorts` destination reads and writes
stored admission cohorts through an adapter, retaining each batch's published
curriculum assignment. Identity replacement clears drafts and guards late saves.

The Sections screen lives in `academic-setup/sections/`, with local `editor/`,
`styles/` and `__tests__/` folders. It reads and writes cohort-owned sections,
selecting a program semester and a dated term. The existing offering-owned
section catalogue remains separate. Student enrollment counts remain unavailable.

`academic-setup/structure/` shares the structure catalogue, identity-safe writes,
forms and drawers used by progression, curriculum and offering screens. Transport
and contracts live in `services/admin/academicStructure.ts` and
`types/academicStructure.ts`; the eight-entity service remains unchanged.
Academic workspace identity includes the authenticated session generation, user,
institution and permissions. Same-session token renewal preserves drafts;
replacement identity or grants discard them.

`features/admin/academic-setup/` follows the owner-selected SQL export: departments,
degree programs, academic years, dated semesters, courses, program-course links,
course offerings and sections. Transport lives in `services/admin/academics.ts`
and contracts in `types/academicSetup.ts`. Form controls and relationship choices
live in `academic-setup/forms/`. Sections belong to one course offering.
Attendance, results and teaching workflows remain out of scope. Student semester
enrollment uses the separate additive registration workflow described above.
The owner asked to keep a specific set of old roster/import/navigation/dashboard
files as source. They remain at their original paths, disconnected from all
active shells. Some import retired dependencies and are not runnable workflows.
The exact inactive source exclusions are in `tsconfig.app.json`; historical tests
for those workflows are individually excluded in `vitest.config.ts`.
`StudentManager.tsx` remains active as an account-approval wrapper and is not
excluded. Active account/profile, approval, information and session tests run.

`check:structure` still checks retained files against maintenance limits and
rejects imports from active source into any exact excluded legacy source path.
Strict TypeScript checking remains enabled for the complete active application.
See the [retirement record](../../docs/retirements/academic-setup/README.md).

## Validation

From `frontend`, run `npm run check:structure`, `npm run build` and `npm test`.
`npm run check` combines them. Format focused changes with
`npx prettier --write <changed-files>`, then rerun structure validation. The
validator checks file length throughout source/scripts/configuration and direct
file counts throughout services, auth, faculty and student features. Check other
affected folders manually against the same shared limit.
