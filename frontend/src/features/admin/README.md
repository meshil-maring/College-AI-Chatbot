# Administration workspace

`AdminShell.tsx` composes account profile, staff/faculty account management,
student account approvals, notices, shared Learning Resources, FAQs, chat and staff permissions.
`adminNavigation.ts` filters operational views using server-resolved grants.
Academic Setup also exposes its static design preview to administrators without
academic grants; catalogue requests and record actions remain gated. Backend
endpoints remain authoritative for authorization and tenant isolation.

`staff-faculty/useStaffFacultyManagement.ts` owns request loading and account
actions. Approved requests expose **Retry sign-in setup** through the existing
approval endpoint, so a provider confirmation failure can be retried without
creating a new registration. Failed decisions refresh the recorded state before
showing the error; late responses from a replaced session are discarded.

| Folder                        | Current responsibility                                                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------- |
| `academic-setup/`             | Departments, programs, years, dated semesters, courses, curriculum links, offerings and sections  |
| `academic-setup/overview/`    | Eleven-entity design overview, academic navigation, search and integration previews               |
| `academic-setup/departments/` | Department list, filters, summaries, add/view/edit drawers and related permission/error states    |
| `academic-setup/programs/`    | Program list, department/degree/status filters, summaries and add/view/edit drawers               |
| `academic-setup/calendar/`    | Academic years, dated semesters, summary cards, filters, dates/timeline and add/view/edit drawers |
| `academic-setup/subjects/`    | Subject catalogue, curriculum assignment filters, credits/hours and add/view/edit drawers         |
| `academic-setup/curriculum/`  | Persisted curriculum versions, publication and history, plus retained existing mappings           |
| `academic-setup/batches/`     | Stored admission cohorts, published curriculum assignment, filters and add/view/edit drawers      |
| `academic-setup/sections/`    | Stored cohort-owned sections, program progression, dated terms and add/view/edit drawers          |
| `academic-setup/structure/`   | Shared structure catalogue, mutation guards, forms and drawers for progression and offerings      |
| `documents/`                  | Retained former document manager; active navigation mounts shared `learning-resources/`           |
| `faqs/`, `notices/`           | Published institution information                                                                 |
| `permissions/`                | Nonacademic staff permission management                                                           |
| `profile/`                    | Administrator identity                                                                            |
| `staff-faculty/`              | Staff and faculty account management                                                              |
| `students/`                   | `StudentManager.tsx` and `AdminApprovals.tsx` retain account decisions                            |

Academic Setup opens on the black-and-yellow overview described in
[the design guide](../../../docs/ACADEMIC_SETUP_DESIGN.md). Its eleven approved
entities use the existing foundation API plus the additive academic-structure API.
Academic and resource drawers share modal focus/scroll behavior through
`../workspace/useWorkspaceDialog.ts`. Learning Resources is owned by the
[shared feature](../learning-resources/README.md), including admin review.
Counts and recent activity come from readable institution records. Existing
catalogues remain accessible without remapping their section or curriculum
relationships. Batches and Sections persist through audited database writes;
unavailable enrollment counts never fall back to sample or capacity numbers.

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
`src/services/admin/`, and contracts in `src/types/`. Keep source and tests
within 250 physical lines and folders within 15 direct maintained files.
