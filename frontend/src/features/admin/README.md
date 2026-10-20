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
