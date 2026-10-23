# Retained legacy UI files

Automatic approval review rejected deletion of the files below because shared
student-management components and dashboards may include retained account,
identity or nonacademic behavior. The active reduced shells preserve approvals,
identity/profile, communication and knowledge features separately. The old source
is also saved in backup commit `77374d0d13fdd2ed61f7a63166a34b8019b91b92`.

On 2026-10-23 the owner chose **Keep these files for now**. The following source
groups remain in the workspace, outside active academic navigation. They are not
part of a replacement academic design. StudentManager's account approval wrapper
remains active where required.

- `frontend/src/features/admin/students/`: `StudentDirectory.tsx`,
  `StudentImport.tsx`, `studentImport.ts`, `StudentImport.test.tsx`,
  `StudentImport.test.ts`, `StudentManager.tsx`, `StudentManager.test.tsx`,
  `studentSections.ts`.
- `frontend/src/features/students/`: `StudentRegistrationInvitations.tsx`,
  `StudentRegistrationInvitations.test.tsx`, `StudentRegistrationWorkflow.test.tsx`,
  `StudentRosterFilters.tsx`, `studentsNavigation.ts`, `studentsNavigation.test.ts`,
  `StudentWorkspaceContext.tsx`.
- `frontend/src/features/admin/shared/adminAcademicQueries.ts`.
- `frontend/src/features/admin/dashboard/`: `AdminDashboard.tsx`,
  `AdminDashboard.test.tsx`, `DashboardCards.tsx`.
- `frontend/src/features/faculty/dashboard/`: `FacultyDashboard.tsx`,
  `FacultyDashboard.test.tsx`.
- `frontend/src/features/student/dashboard/`: `StudentDashboard.tsx`,
  `StudentDashboard.test.tsx`, `StudentDashboardEdgeCases.test.tsx`,
  `StudentDashboardHardening.test.tsx`, `StudentDashboardIntegration.test.tsx`,
  `StudentDashboardStates.test.tsx`.
- `frontend/src/types/admin/dashboard.ts`.
- `frontend/src/features/student/shared/AcademicContextCard.tsx`.

These files must remain until the owner requests their removal. Inactive legacy
code may still describe retired API contracts; it must not re-enable academic
endpoints or require recreating the removed database tables.
