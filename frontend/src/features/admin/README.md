# Administration workspace

`AdminShell.tsx` composes account profile, staff/faculty account management,
student account approvals, notices, documents, FAQs, chat and staff permissions.
`adminNavigation.ts` filters operational views using server-resolved grants.
Academic Setup also exposes its static design preview to administrators without
academic grants; catalogue requests and record actions remain gated. Backend
endpoints remain authoritative for authorization and tenant isolation.

| Folder                     | Current responsibility                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| `academic-setup/`          | Departments, programs, years, dated semesters, courses, curriculum links, offerings and sections |
| `academic-setup/overview/` | Eleven-entity design overview, academic navigation, search and integration previews              |
| `documents/`               | Documents and knowledge sources                                                                  |
| `faqs/`, `notices/`        | Published institution information                                                                |
| `permissions/`             | Nonacademic staff permission management                                                          |
| `profile/`                 | Administrator identity                                                                           |
| `staff-faculty/`           | Staff and faculty account management                                                             |
| `students/`                | `StudentManager.tsx` and `AdminApprovals.tsx` retain account decisions                           |

Academic Setup opens on the black-and-yellow overview described in
[the design guide](../../../docs/ACADEMIC_SETUP_DESIGN.md). Its eleven approved
entities remain distinct from the existing eight-entity service contract.
Only departments, programs, years and subjects use matching catalogue counts;
unsupported areas are explicitly labeled design previews. Existing catalogues
remain accessible without remapping their section or curriculum relationships.

Academic Setup uses focused hooks, typed contracts and identity-scoped query keys.
Semesters have dates within academic years. Courses are teaching subjects;
programs are degrees. Link a course to its program before creating an offering
for a year and semester. A section belongs to one offering, with optional capacity.
Form definitions and ancestry-filtered choices live in `academic-setup/forms/`.
Parent references and section codes are immutable; active children prevent
parent deactivation. Attendance, results and teaching workflows remain removed.
Legacy roster/import helpers and the old dashboard remain as
source at the owner's request; they are disconnected from the active shell.
See the [removal record](../../../../docs/retirements/academic-setup/README.md).
Their exact exclusions are in `tsconfig.app.json` and `vitest.config.ts`.
`check:structure` checks their maintenance limits and rejects active imports into
excluded legacy source. Student account approval tests remain active.

Keep state and requests in focused hooks, rendering in components, transport in
`src/services/admin/`, and contracts in `src/types/admin/`. Keep source and tests
within 250 physical lines and folders within 15 direct maintained files.
