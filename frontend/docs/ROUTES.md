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
Administrator views are Profile, Staff & Faculty, Student Approvals, Notices,
Documents, FAQs, AI Assistant and Staff Permissions. Staff views are Profile,
Student Approvals and AI Assistant. Student views are Profile, Notices, Learning
Resources and AI Assistant after account approval. Server permissions filter
navigation, and backend endpoints enforce authorization and tenant isolation.

Legacy roster hash-navigation helpers remain as disconnected source at the
owner's request. Old Academic Setup/dashboard navigation is not active. See the
[removal record](../../docs/retirements/academic-setup/README.md).
