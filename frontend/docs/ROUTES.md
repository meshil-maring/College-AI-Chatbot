# Faculty routes

Faculty navigation uses the browser History API. Direct links, refresh, and browser Back/Forward resolve the same view. Faculty routes require a restored faculty session; section permissions are loaded from the server before showing registration.

| URL | Page |
| --- | --- |
| `/faculty` | Dashboard |
| `/faculty/assignments` | My Sections |
| `/faculty/students` | Students (roster entry point) |
| `/faculty/students/roster` | All Student |
| `/faculty/students/subject-assignment` | Subject Assignment |
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
| `/faculty/subject-packages` | Subject packages, class placements, change requests, and history in authorized academic scope |

All five Students pages accept `?section_id=<section UUID>`. Their navigation links and section selector preserve the selected page and section. Register includes a Section and subject selector listing only sections the faculty account can manage; it is disabled while saving. An unavailable or read-only section cannot be used to register a student. Saving or cancelling returns to the selected roster. Without a section parameter, registration selects the first section the faculty account can manage.

Subject Assignment lists saved class registrations missing the selected subject. Course, branch, section, semester, subject, and batch filters preserve academic scope. Assigning a student adds their saved identity to that subject roster, preserves account approval status, and removes them from the missing list. Read-only sections and identity conflicts cannot be assigned. Admin uses `#admin/students/subject-assignment`; Faculty uses the URL above.

Record history reads saved roster activity and account reconciliation events through the section-scoped registration-history endpoint. Older/imported additions without individual audit entries use the roster's stored creation timestamp. Waiting approval always requests `PENDING_APPROVAL` records in the selected section; faculty do not gain approval permissions from this page.

Subject Packages is visible when the faculty context carries the relevant active
responsibility capabilities. The server catalogue also supplies per-class
assignment/change/review permissions. Admin Academic Setup groups curriculum,
class setup, and package assignment beside the existing master records. The
existing Subject Assignment page links to complete package assignments. Staff
receive a Subject Packages navigation entry only through explicit delegation;
students receive My Subject Package through their own-package permissions.
Staff, admin setup groups, and student package tabs use their existing shell
navigation state rather than introducing additional URL routes.

Vite development and preview servers provide the HTML fallback for direct links. A production static host must serve `index.html` for frontend routes, preserve the query string, and continue routing `/api` to the backend.
