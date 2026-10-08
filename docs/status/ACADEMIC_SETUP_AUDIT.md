# Academic setup audit

Audited before implementation on 2026-10-08. Existing unrelated working-tree changes are retained.

| Entity | Authoritative table / relationship | Existing management |
|---|---|---|
| Institution | `institutions`; tenant root | Platform institution lifecycle screens and APIs |
| Department | `departments.institution_id`; optional tenant-consistent campus | No academic CRUD API or Admin screen |
| Program | `programs.department_id` | No academic CRUD API or Admin screen |
| Academic year | `academic_years.institution_id`; dates, current/active flags | No academic CRUD API or Admin screen |
| Semester | `semesters.academic_year_id`; number, dates, current/active flags | No academic CRUD API or Admin screen |
| Subject definition | `courses.department_id`; code, credits, contact hours | No academic CRUD API or Admin screen |
| Program curriculum | `program_courses(program_id, course_id)`; optional semester, course type | No management UI; required by offering composite FK |
| Offering | `course_offerings(course_id, program_id, academic_year_id, semester_id)` | No academic CRUD API or Admin screen |
| Subject section | `sections.course_offering_id`; code, name, capacity, active flag | Faculty Assignment reads these records; no setup UI |
| Student identity | `students.user_id` -> `users.id`; institution, optional program/year | Existing Admin Student CRUD, approval and self-registration |
| Section enrollment | `faculty_attendance_rosters`; section/offering/semester and optional `linked_student_id` | Existing authorized Faculty roster entry/import and reconciliation |
| Faculty | `users` plus active institution-scoped faculty role grant | Existing Staff & Faculty roster/onboarding |
| Teaching responsibility | `faculty_section_assignments`, scoped `faculty_responsibilities` | Existing Faculty Assignment and responsibility screens/APIs |

The existing hierarchy is institution -> department -> program, with institution-owned academic years and year-owned semesters. Offerings join program, subject, year and semester. Sections are subject-specific, not a separate cohort table. Sibling subject sections share `(program_id, academic_year_id, semester_id, section code)` for class scope. Subjects from another department in the same institution are supported through `program_courses`. Creating a second program-semester hierarchy or cohort table would contradict existing authorization.

Existing unique constraints protect department codes per institution, program/course codes per department, year codes per institution, semester code/number per year, offerings per course/program/year/semester, and section codes per offering. Partial indexes enforce one current year per institution and one current semester per year. Semester/year consistency and curriculum membership already have composite foreign keys.

Existing granular permissions include `departments.read/manage`, `courses.read/manage`, `subjects.read/manage`, `academic_years.read/manage`, and `semesters.read/manage`. University Admin's canonical institution role is `admin`; existing institution authorization resolves active account, role and institution server-side. Staff's delegable permission set excludes global academic setup. Faculty responsibilities grant scoped reporting/assignment capabilities, not master-data management. Reuse `departments.*` for programs and `courses.*` for curriculum, offerings and sections; no additional role or permission catalogue is needed.

Existing `admin_audit_log` supports actor, tenant, action, record and before/after JSON. Academic mutations need an atomic database operation so an audit failure cannot leave an unaudited change.

Missing database safeguards: authoritative master tables currently grant service-role access without RLS; most relationship FKs do not enforce cross-tenant ownership or active parents. Safe setup needs service-only, audited writes; explicit relationship and date checks; protection against reparenting existing records; case/whitespace-insensitive code uniqueness; and concurrent enforcement of date overlap/current rules. Preserve existing tables and foreign keys. Do not seed academic data.

Student dependency: a real approved student identity and program/year must exist, then the existing roster workflow must enroll/reconcile that student into actual subject sections. Setup does not create students or rosters. Student Academic Experience continues to derive identity/eligibility from its existing services.
