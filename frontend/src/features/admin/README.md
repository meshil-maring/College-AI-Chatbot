# Administration workspace

`AdminShell.tsx` composes account profile, staff/faculty account management,
student account approvals, notices, documents, FAQs, chat and staff permissions.
`adminNavigation.ts` filters those views using server-resolved grants. Backend
endpoints remain authoritative for authorization and tenant isolation.

| Folder              | Current responsibility                                                 |
| ------------------- | ---------------------------------------------------------------------- |
| `documents/`        | Documents and knowledge sources                                        |
| `faqs/`, `notices/` | Published institution information                                      |
| `permissions/`      | Nonacademic staff permission management                                |
| `profile/`          | Administrator identity                                                 |
| `staff-faculty/`    | Staff and faculty account management                                   |
| `students/`         | `StudentManager.tsx` and `AdminApprovals.tsx` retain account decisions |

Academic Setup, curricula/packages, attendance, results and teaching assignments
have been removed. Legacy roster/import helpers and the old dashboard remain as
source at the owner's request; they are disconnected from the active shell.
See the [removal record](../../../../docs/retirements/academic-setup/README.md).
Their exact exclusions are in `tsconfig.app.json` and `vitest.config.ts`.
`check:structure` checks their maintenance limits and rejects active imports into
excluded legacy source. Student account approval tests remain active.

Keep state and requests in focused hooks, rendering in components, transport in
`src/services/admin/`, and contracts in `src/types/admin/`. Keep source and tests
within 250 physical lines and folders within 15 direct maintained files.
