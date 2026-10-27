# Authenticated workspace routes

Faculty uses the browser History API. Direct links, refresh and Back/Forward
resolve the same view after the faculty identity has been restored.

| URL                            | Page                                       |
| ------------------------------ | ------------------------------------------ |
| `/faculty`, `/faculty/profile` | Faculty identity profile                   |
| `/faculty/notices`             | Existing notices availability placeholder  |
| `/faculty/resources`           | Existing resource availability placeholder |
| `/faculty/assistant`           | AI Assistant                               |

Removed faculty routes for assignments, rosters, attendance, results, departments,
classes and subject packages are no longer recognized by the application route
parser. They do not mount an academic screen or call its former endpoints.

Administrator and staff shells use local view state and start on Profile.
Administrator views are Profile, Academic Setup, Staff & Faculty, Student Approvals, Notices,
Documents, FAQs, AI Assistant and Staff Permissions. Staff views are Profile,
Student Approvals and AI Assistant. Student views are Profile, Notices, Learning
Resources and AI Assistant after account approval. Server permissions filter
navigation, and backend endpoints enforce authorization and tenant isolation.

Academic Setup opens on an overview with local view navigation for the eleven
approved entities. Academic Calendar groups Years and Terms; Curriculum groups
Versions and Subjects. Its existing catalogue workflow is preserved separately.
See the [Academic Setup design guide](ACADEMIC_SETUP_DESIGN.md).

Legacy roster hash-navigation helpers and old dashboard navigation remain as
disconnected source at the owner's request. See the
[removal record](../../docs/retirements/academic-setup/README.md).
