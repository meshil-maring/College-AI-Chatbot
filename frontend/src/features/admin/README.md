# Administration workspace

`AdminShell.tsx` composes account profile, Staff and Faculty Management (requests,
departments, roster and staff permissions on one page), student account approvals,
notices, shared Learning Resources, FAQs and chat.
`adminNavigation.ts` filters operational views using server-resolved grants.
`navigation/useAdminWorkspaceNavigation.ts` keeps views, academic destinations
and search in validated URL parameters for refresh and Back/Forward navigation.
The Students sidebar groups All Students, Add Student, Bulk Import and
Registration Requests; the bulk route reuses the guarded invitation workflow
with row search, validation filters and paginated review.
Academic Setup's `navigation/` owns the guided setup path and contextual next
actions; its sidebar exposes options and enrollment directly.
Academic Setup also exposes its static design preview to administrators without
academic grants; catalogue requests and record actions remain gated. Backend
endpoints remain authoritative for authorization and tenant isolation.

`staff-faculty/useStaffFacultyManagement.ts` owns request loading and account
actions. The administrator chooses each new member's department when approving
(`requests/MembershipRequests.tsx`) and can change it from `roster/MembershipRosterTable.tsx`;
applicants no longer pick a department. The administrator also confirms Staff or
Faculty on approval and can switch it from the roster; the server refuses a switch
while the member is a current Head of Department or holds extra Staff permissions.
Staff and Faculty Management has six sidebar pages (`StaffFacultyNavigation.tsx`,
`staff-page` in the URL): Requests, Pending invitations, Roster, Responsibilities,
Administrators and Staff permissions.
`StaffFacultyManager.tsx` renders the chosen page; reads stay cached across pages.
The roster is the user directory: `roster/directoryItems.ts` merges members, administrators
(`roster/useDirectoryAdmins.ts`) and pending invitations, which show read-only
(`roster/DirectoryReadOnlyRow.tsx`) and link to the page that manages them. Filters cover
user type, status (active, invitation pending, suspended, inactive), department, employment
type and employment status; search also matches employee ID and designation.
**Edit profile** (`profile/EditProfileDialog.tsx`, `profile/useEditProfile.ts`) reuses the Add
member fields to change the employee profile and departments; **History**
(`history/MemberHistoryDialog.tsx`) lists who changed what from the audit log.
Each roster row keeps its actions (Edit profile, History, Manage HOD, Permissions,
Suspend, Deactivate/Reactivate) in one
**Actions** menu (`roster/RowActionsMenu.tsx`), portalled so the table scroll never clips it.
The roster shows one HOD badge per department a member heads, and **Manage HOD**
(`roster/HodDialog.tsx`, `useDepartmentHeadActions.ts`) lets the administrator tick
every department an active Faculty member heads. A department may have several
equal heads and a head may lead any active department; changes are saved as single
add/end appointment calls. HOD is an appointment on top of Faculty, not a separate role. The roster's Permissions button opens that
Staff member in the embedded `permissions/StaffPermissionManager.tsx`. Approved requests expose **Retry sign-in setup** through the existing
approval endpoint, so a provider confirmation failure can be retried without
creating a new registration. Failed decisions refresh the recorded state before
showing the error; late responses from a replaced session are discarded.
`StaffFacultySummary.tsx` shows pending, active Faculty/Staff and unassigned counts;
`roster/useRosterFilters.ts` searches and filters the loaded roster in the browser,
and `StaffFacultyUI.tsx` holds the page's shared buttons, badges and dismissible feedback.
**Add member** (`invitations/AddMemberDialog.tsx`) invites new Staff or Faculty in
three steps from `invitations/add-member/`: basic details (`BasicDetailsStep.tsx`:
name, email, phone, employee ID, designation, joining date, user type), role details
(`RoleDetailsStep.tsx` with `DepartmentFields.tsx` for primary and additional
departments and `ResponsibilitiesField.tsx` for Staff), and `ReviewStep.tsx`.
`useAddMemberDraft.ts` holds the draft and validates each step; `memberDraft.ts`
mirrors the server rules and builds the request with the employee profile.
`invitations/useMemberInvitations.ts` owns the pending list and resend/cancel, and
`invitations/PendingInvitations.tsx` renders it (expired links offer **Invite again**).
The person accepts through the existing invitation page; the database then records an
approved membership request decided by the inviting administrator, grants the role and
assigns the departments and employee profile together (`20261127000000` to
`20261128020000` migrations).
**Responsibilities** (`responsibilities/`) are dated extra duties of Faculty, not roles.
Heads of Department are appointed from the roster: `roster/HodDialog.tsx` gives each
department a start date and optional planned end (`roster/HodTermFields.tsx`, UTC dates
like the server) and respects the institution's one-department rule;
`useDepartmentHeadActions.ts` ends, adds and re-dates appointments. `ResponsibilitiesPage.tsx`
switches that rule and manages Class In-Charge (a class section) and Subject Coordinator
(a catalogue course) through `useMemberResponsibilities.ts`; each section or course has
one current holder, and history is kept (`20261129000000`/`20261129010000` migrations).
**Administrators** (`administrators/`) lists everyone who administers the institution.
Every administrator has full access; the Owner alone invites (`InviteAdminForm.tsx`),
removes administrators and transfers ownership, and the server enforces that
(`useInstitutionAdmins.ts`, `20261130000000` to `20261130020000` migrations).
The embedded permission list (`permissions/StaffPermissionList.tsx`) shows role grants
read-only beside delegable permissions with readable labels.

| Folder                                     | Current responsibility                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `academic-setup/`                          | Departments, programs, years, dated semesters, courses, curriculum links, offerings and sections                                                                                                                                                                                                                                                                                                                                 |
| `academic-setup/overview/`                 | Eleven-entity design overview, academic navigation, search and integration previews                                                                                                                                                                                                                                                                                                                                              |
| `academic-setup/departments/`              | Department list, filters, summaries, add/view/edit drawers and related permission/error states                                                                                                                                                                                                                                                                                                                                   |
| `academic-setup/programs/`                 | Program list, department/degree/status filters, summaries and add/view/edit drawers                                                                                                                                                                                                                                                                                                                                              |
| `academic-setup/calendar/`                 | Academic years, dated semesters, summary cards, filters, dates/timeline and add/view/edit drawers                                                                                                                                                                                                                                                                                                                                |
| `academic-setup/subjects/`                 | Subject catalogue, curriculum assignment filters, credits/hours and add/view/edit drawers                                                                                                                                                                                                                                                                                                                                        |
| `academic-setup/curriculum/`               | Persisted curriculum versions, publication and history, plus retained existing mappings                                                                                                                                                                                                                                                                                                                                          |
| `academic-setup/batches/`                  | Stored admission cohorts, published curriculum assignment, filters and add/view/edit drawers                                                                                                                                                                                                                                                                                                                                     |
| `academic-setup/sections/`                 | Stored cohort-owned sections, program progression, dated terms and add/view/edit drawers                                                                                                                                                                                                                                                                                                                                         |
| `academic-setup/structure/`                | Shared structure catalogue, mutation guards, forms and drawers for progression and offerings                                                                                                                                                                                                                                                                                                                                     |
| `academic-setup/registration/`             | Administrator semester assignments and registration query state                                                                                                                                                                                                                                                                                                                                                                  |
| `academic-setup/curriculum/choices/`       | Semester-scoped choice groups embedded beside compulsory and optional subjects                                                                                                                                                                                                                                                                                                                                                   |
| `academic-setup/curriculum/semester-plan/` | Semester subject cards, preset subject drawers and explicit publication review                                                                                                                                                                                                                                                                                                                                                   |
| `documents/`                               | Retained former document manager; active navigation mounts shared `learning-resources/`                                                                                                                                                                                                                                                                                                                                          |
| `faqs/`, `notices/`                        | Published institution information                                                                                                                                                                                                                                                                                                                                                                                                |
| `permissions/`                             | Staff permission section embedded in Staff and Faculty Management |
| `profile/`                                 | Administrator identity                                                                                                                                                                                                                                                                                                                                                                                                           |
| `staff-faculty/`                           | Staff and Faculty Management: requests, departments, roster and the embedded staff permissions |
| `students/`                                | `StudentManager.tsx` provides Register Students and the URL-backed All Students directory. The directory combines institution-scoped student profiles and pending invitations, with sign-in state, latest Course/Branch/Batch/Section placement, search, program filters and pagination. Row Actions support audited profile edits, access deactivation/reactivation, deletion only when no records are linked, and pending invitation edits/cancellation. Authenticated admins may correct a pending invitation email; this rotates the setup token and sends a fresh link. Registered student email remains read-only pending its separate verification flow. `student-onboarding/` guides single and CSV/XLSX registration through placement, duplicate-account/sign-in review, and delivery results |

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
Departments, programs, calendar years/semesters and cohort-owned class sections
expose a confirmed Delete action for unused records. Academic Setup's shared
`deletion/` owns the dialog, eligibility model, styles and guarded mutations.
Current periods and known links block confirmation. The backend checks every
link, including inactive curricula, batches, offerings and student registrations.
Read-only users have no Delete action, and identity replacement clears pending UI.
Legacy roster/import helpers and the old dashboard remain as
source at the owner's request; they are disconnected from the active shell.
See the [removal record](../../../../docs/retirements/academic-setup/README.md).
Their exact exclusions are in `tsconfig.app.json` and `vitest.config.ts`.
`check:structure` checks their maintenance limits and rejects active imports into
excluded legacy source. Student account approval tests remain active.

Keep state and requests in focused hooks, rendering in components, transport in
`src/services/admin/`, and contracts in `src/types/`. Keep source and tests
within 250 physical lines and folders within 15 direct maintained files.
