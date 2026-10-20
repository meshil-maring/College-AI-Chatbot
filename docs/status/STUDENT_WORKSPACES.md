# Shared Students UI

Admin, Staff, and Faculty use the components in
`frontend/src/features/students/StudentsUI.tsx` and the shared
`students.css` stylesheet for Students sidebar links, page headings,
status cards, search forms, and registration method tabs.

Students pages stay in the sidebar. Individual Registration and Bulk
Registration are tabs within the registration page. Search uses the same
submit/Enter interaction across student directories and approval queues.
Tables scroll within their container on small screens.

Admin and Faculty use the same submenu order: Roster, Record history,
Waiting approval, Register. These names come from one shared navigation
definition. Student Approvals no longer has a separate top-level Admin menu
item; dashboard approval shortcuts open Students → Waiting approval.
Admin and Staff submenu links persist in the URL so refresh, bookmarks,
and browser Back/Forward restore the selected Students page. Admin Register
also preserves the selected registration method. Earlier Admin submenu
bookmarks are supported.

Admin and Staff render one `StudentApprovalQueue` component through their
existing approval entry points. It retains tenant-scoped API calls, decision
locking, conflict recovery, and safe loading/error/empty states, with search
and pagination. Internal student/account/institution IDs are not displayed.

Admin and Faculty now render the same `StudentWorkspace` from
`features/faculty/FacultyStudents.tsx`, including its roster, class-registration
directory, registration history, details, and registration components.
`StudentWorkspaceContext` supplies role-specific API functions and query keys.
Admin calls only `/admin/student-workspace/*`; Faculty continues calling its
existing endpoints. Admin has the full workflow:

- Roster: institution section selection, status counts, search/filter/sort,
  pagination, student details and recorded subject attendance history.
- Record history: the same section-scoped registration, roster and account
  events as Faculty, including actions by other authorized users. It replaces
  the previous capped, actor-only audit preview.
- Waiting approval: the same section waiting lists plus Admin's institution
  account approval queue and approve/reject actions.
- Register: Course, Branch, Section and saved admission Batch selection;
  individual saves and bulk upload, validation, duplicate/conflict checks,
  selected-row confirmation, actual saves, results, reports and failure retries.

Roster filters use separate Course, Branch, Batch, Section and Semester dropdowns
in `features/students/StudentRosterFilters.tsx`. Subject appears separately when
the selected class has more than one authorized subject. Changing a branch clears
an incompatible cohort; batch changes retain search/status and reset pagination.
Both roster lists apply cohort, search and registration-status filters on the
server before pagination. Status counts respect the selected cohort. Archived
cohorts remain available for viewing, while new registration still requires an
active batch. Subject-roster cohort matching uses saved student identifiers within
the institution and branch, so admission batches persist across semester/section
changes. Older rosters without a saved admission cohort appear under All batches.

Existing permissions govern the new Admin routes. Roster/details/history require
`students.read` and `attendance.read`. Registration requires `students.create`;
batch and class-registration reads require `students.read`. Admin does not need
a teaching assignment; every section and record remains institution scoped.
Record history uses the same safe student-event projection as Faculty, rather
than granting general audit-log access. Account approvals keep their existing
permissions and endpoints.

Other role boundaries remain unchanged:

- Staff has Students → Waiting approval and permitted approval decisions.
  Staff receives no directory, registration, or faculty API access.
- Faculty retains authorized section rosters, record history, pending account
  status, and individual/bulk class registration. Faculty cannot approve accounts.

The shared `WorkspaceFrame` gives Admin and Staff the same responsive sidebar
behavior. Faculty keeps its existing routed shell and uses the shared Students
links and content components within it.

The existing student-registration and academic-batch migrations documented in
`STUDENT_CLASS_REGISTRATION.md` must be applied before saves are available.
This parity change adds no further database migration.
