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
Administrator views are Profile, Academic Setup, Staff & Faculty, Student Approvals, Notices,
Learning Resources, FAQs, AI Assistant and Staff Permissions. Staff views are Profile,
Student Approvals, Learning Resources and AI Assistant. Student views are Profile, Notices, Learning
Resources, Semester Registration and AI Assistant after account approval. Server permissions filter
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

Administrator links retain the current application entry path and use `view`,
`academic` and `academic-search` query parameters. For example,
`/?view=academic-setup&academic=curriculum-subjects` opens compulsory subjects and
student choice groups together after authentication. Existing `curriculum-options`
links resolve to this combined destination. Unknown destinations fall back safely. Search replaces the current
overview entry while typing; choosing another page clears the search. URL values
select presentation only and never authorize catalogue reads or mutations.

Legacy roster hash-navigation helpers and old dashboard navigation remain as
disconnected source at the owner's request. See the
[removal record](../../docs/retirements/academic-setup/README.md).
