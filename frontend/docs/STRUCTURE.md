# Frontend structure

The app uses React, TypeScript, Vite and TanStack Query. State belongs in feature
hooks, rendering in focused components, transport in `services/` and contracts in
`types/`. Follow the [shared rules](../../AGENTS.md) before creating or moving files.

Keep every maintained code, test, stylesheet and script within 250 physical lines
and each folder within 15 directly contained maintained files. Inspect nearby
implementations first; reuse ownership boundaries and avoid forwarding modules.
Dependencies, generated output and local verification logs are excluded from
maintenance limits. Logs belong in repository-level `logs/frontend/`.

| Location                                   | Responsibility                                                         |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| `src/main.tsx`, `src/App.tsx`              | Bootstrap and public/authenticated route composition                   |
| `src/app/`                                 | Path parsing, authentication gates and identity-scoped workspaces      |
| `src/features/auth/`                       | Session, sign-in, password, registration and server-grant helpers      |
| `src/features/admin/`                      | Institution account administration, approvals and knowledge management |
| `src/features/staff/`                      | Staff identity, student account approvals and chat                     |
| `src/features/faculty/`                    | Faculty profile, existing information placeholders and chat            |
| `src/features/student/`                    | Identity/approval gate, notices, resources and chat                    |
| `src/features/students/`                   | Shared account-approval UI and retained inactive roster source         |
| `src/features/superAdmin/`                 | Institution and administrator lifecycle                                |
| `src/features/publicChat/`                 | Institution public chat and history storage                            |
| `src/services/`                            | Domain API clients and session-expiry events                           |
| `src/types/`                               | Backend request/response contracts                                     |
| `src/hooks/`, `src/lib/`, `src/providers/` | Shared query, navigation and providers                                 |
| `src/test/`, workflow `__tests__/`         | Test setup and fixtures                                                |

See the [admin](../src/features/admin/README.md),
[faculty](../src/features/faculty/README.md),
[student](../src/features/student/README.md),
[auth](../src/features/auth/README.md) and
[services](../src/services/README.md) guides for ownership. Feature consumers may
use domain service/type facades; implementation modules import siblings directly.
Preserve public import contracts, mock paths, identity keys, cancellation and
server-authoritative permissions when extracting code. Keep CSS import order.

## Retained inactive source

`features/admin/academic-setup/` follows the owner-selected SQL export: departments,
degree programs, academic years, dated semesters, courses, program-course links,
course offerings and sections. Transport lives in `services/admin/academics.ts`
and contracts in `types/academicSetup.ts`. Form controls and relationship choices
live in `academic-setup/forms/`. Sections belong to one course offering.
Attendance, results, enrollment and teaching workflows remain out of scope.
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
