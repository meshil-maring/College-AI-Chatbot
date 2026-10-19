# Faculty routes

Faculty navigation uses the browser History API. Direct links, refresh, and browser Back/Forward resolve the same view. Faculty routes require a restored faculty session; section permissions are loaded from the server before showing registration.

| URL | Page |
| --- | --- |
| `/faculty` | Dashboard |
| `/faculty/assignments` | My Sections |
| `/faculty/students` | Students (roster entry point) |
| `/faculty/students/roster` | Roster |
| `/faculty/students/record-history` | Student registration activity |
| `/faculty/students/waiting-approval` | Students awaiting account approval |
| `/faculty/students/register` | Register new student |
| `/faculty/attendance` | Attendance |
| `/faculty/results` | Results |
| `/faculty/notices` | Notices |
| `/faculty/resources` | Learning Resources |
| `/faculty/assistant` | AI Assistant |
| `/faculty/profile` | Profile |
| `/faculty/class-management` | Class Management |
| `/faculty/department` | Department |
| `/faculty/teaching-assignments` | Teaching Assignments |

All four Students pages accept `?section_id=<section UUID>`. Their navigation links and section selector preserve the selected page and section. Register includes a Section and subject selector listing only sections the faculty account can manage; it is disabled while saving. An unavailable or read-only section cannot be used to register a student. Saving or cancelling returns to the selected roster. Without a section parameter, registration selects the first section the faculty account can manage.

Record history reads saved roster activity and account reconciliation events through the section-scoped registration-history endpoint. Older/imported additions without individual audit entries use the roster's stored creation timestamp. Waiting approval always requests `PENDING_APPROVAL` records in the selected section; faculty do not gain approval permissions from this page.

Vite development and preview servers provide the HTML fallback for direct links. A production static host must serve `index.html` for frontend routes, preserve the query string, and continue routing `/api` to the backend.
