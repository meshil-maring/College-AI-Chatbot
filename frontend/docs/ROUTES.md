# Authenticated workspace routes

Faculty uses the browser History API. Direct links, refresh and Back/Forward
resolve the same view after the faculty identity has been restored.

| URL                            | Page                                              |
| ------------------------------ | ------------------------------------------------- |
| `/faculty`, `/faculty/profile` | Faculty identity profile                          |
| `/faculty/notices`             | Existing notices availability placeholder         |
| `/faculty/resources`           | Shared Learning Resources library and submissions |
| `/faculty/assistant`           | AI Assistant                                      |

Removed faculty routes for assignments, rosters, attendance, results, departments,
classes and subject packages are no longer recognized by the application route
parser. They do not mount an academic screen or call its former endpoints.

Administrator navigation uses validated URL query parameters and starts on Profile
when no destination is supplied. Browser Back/Forward and refresh retain the
selected view. Staff navigation continues to use local view state.
Administrator views are Profile, Academic Setup, Staff and Faculty Management, Student registration and approvals,
Notices, Learning Resources, FAQs and AI Assistant. Old `view=permissions` links open its Staff permissions page. Staff views are Profile,
Student Approvals, Learning Resources and AI Assistant. Student views are Dashboard (the default),
Profile, Notices, Learning Resources, Semester Registration, Transfer Requests,
Notifications and AI Assistant after account approval. Server permissions filter
navigation, and backend endpoints enforce authorization and tenant isolation.
Admin, faculty and staff mount the same resource page; exact grants control
library, own submissions, uploads and admin review. Only Notices remains a faculty
availability placeholder.

Academic Setup opens on an overview for the eleven setup entities and student
enrollment. Its grouped sidebar exposes Subjects by semester, Version History and
Student Enrollment directly. A compact setup guide links Foundations, Curriculum,
Batches, Classes & subjects and Student enrollment, with next actions on each page.
Curriculum and calendar tabs share their destination with the sidebar, including
Important Dates and Overview Timeline. Active tabs stay visible on narrow screens. Sections also
links directly to enrollment; students complete Semester Registration in their portal.
Its existing catalogue workflow is preserved separately.
See the [Academic Setup design guide](ACADEMIC_SETUP_DESIGN.md).

## Sign-in and signup routes

Everyone signs in at one page, `/login`: students, faculty, staff and university
admins. The form never asks for a role. The server resolves the account's role
after sign-in and opens the matching workspace. `?institution=<CODE>` pre-fills
the institution code for register or roll-number sign-in. Retired
`/login/student`, `/login/faculty`, `/login/staff` and `/login/admin` links
redirect to `/login` and keep their other query values. Protected workspace URLs
such as `/super-admin` and `/faculty/*` show the same sign-in form in place.

Each self-registering account type has its own public signup page:

| URL               | Page                                                  |
| ----------------- | ----------------------------------------------------- |
| `/signup/student` | Student registration (register or roll number)        |
| `/signup/faculty` | Faculty registration (designation and department)     |
| `/signup/staff`   | Staff registration (designation and department)       |

Each page accepts an optional `?institution=<CODE>` to pre-fill the institution.
The path only selects the form. The server decides the role and creates a
pending account that an institution reviewer must approve. A visitor who is
already signed in is asked to sign out before continuing. Admin and Super Admin
accounts have no public signup page; they use `/register/university`,
`/register/super-admin` and invitation links. Old `/login/<type>?register=1`
links redirect to the matching signup page. Paths are built in
`features/auth/login/loginPaths.ts` and `features/auth/registration/signupPaths.ts`.

The public `/student-setup#<single-use-token>` route verifies an admin-created
student invitation and sets the student's password. The token stays in the URL
fragment until the client submits it to the backend.

Administrator links retain the current application entry path and use `view`,
`academic`, `academic-search`, `student-page` and `staff-page` query parameters. For example,
`/?view=academic-setup&academic=curriculum-subjects` opens compulsory subjects and
student choice groups together after authentication. Existing `curriculum-options`
links resolve to this combined destination. Unknown destinations fall back safely. Search replaces the current
overview entry while typing; choosing another page clears the search. URL values
select presentation only and never authorize catalogue reads or mutations.
The Students workspace uses `student-page=all`, `student-page=bulk`, and
`student-page=requests`; Add Student is the default when no student page is set.
Staff and Faculty Management uses `staff-page=invitations`, `staff-page=roster` and
`staff-page=permissions`; Requests is the default. Old `view=permissions` links open
the Staff permissions page, which is hidden (and falls back to Requests) without
`permissions.read`.

Legacy roster hash-navigation helpers and old dashboard navigation remain as
disconnected source at the owner's request. See the
[removal record](../../docs/retirements/academic-setup/README.md).
