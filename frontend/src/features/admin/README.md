# Admin frontend

Keep each section's components, helpers, and tests in its own folder.
`AdminShell.tsx` composes the sections; `adminNavigation.ts` defines their
navigation labels, headings, and permission visibility.

| Folder | Section |
| --- | --- |
| `academic-setup/` | Academic setup, entity definitions, and field help |
| `attendance/` | Attendance records |
| `dashboard/` | Dashboard overview and quick actions |
| `documents/` | Documents and knowledge sources |
| `faculty-assignments/` | Teaching assignments, responsibilities, and validity editing |
| `faqs/` | FAQ management |
| `notices/` | Notice management |
| `permissions/` | Staff permissions |
| `profile/` | Admin profile and identity card |
| `results/` | Student results and CSV uploads |
| `staff-faculty/` | Staff and faculty management |
| `students/` | Student records and student approvals |
| `test-results/` | Test results |
| `shared/` | Query keys and invalidation shared across admin sections |

The AI Assistant uses the existing `../chat/ChatShell.tsx`. Shared API clients,
types, and hooks remain in `src/services`, `src/types`, and `src/hooks`.

Academic Setup keeps its request and form lifecycle in `academic-setup/useAcademicSetup.ts`
and directory filtering, selection, and pagination in `useAcademicDirectory.ts`.
Its `ui/` folder owns summary cards, tables, record details, forms, and setup guidance;
`styles/` contains the scoped dark and yellow theme. The UI calls degree programs
“Courses” and keeps individual subjects in the “Subjects” workflow. All nine
catalogue entities retain their existing API contracts and permission projections.

Academic Setup also composes `../academic-packages/` through focused groups for
named curricula/packages, Class Setup, and complete Package Assignment. That
shared feature owns typed package forms, class policy/teaching mappings,
placements, change requests, review, and revision history. Transport lives in
`services/academics/`; student, staff, and scoped faculty shells reuse the same
workflow with server-projected capabilities.

Course Offering selectors combine existing Program Curriculum links with the
catalogue's `offering_eligibility` metadata for named classes. Named eligibility
matches the exact program, subject, and dated teaching term; it enables offering
creation without writing a separate legacy curriculum link. Subjects are then
offered, divided into teaching sections, and mapped back to the shared class.
