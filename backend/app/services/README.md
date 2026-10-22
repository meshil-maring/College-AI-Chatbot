# Backend services

Follow the shared [backend structure rules](../../STRUCTURE.md).

Services are grouped by feature. API routers call these modules; repositories
continue to own database access and schemas continue to own request/response types.

| Package | Related services |
| --- | --- |
| `academics/` | Academic setup, curriculum/package workflows, atomic legacy roster adapters, verified managed study-progression projections, attendance and results |
| `admin/` | Admin academics, dashboard, documents, FAQs, memberships and notices |
| `ai/` | Authenticated/public chat, conversation history and intent, context, generation, personalization and query rewriting |
| `auth/` | Sign-in, sessions, account registration, authorization, RBAC and shared request-abuse controls |
| `email/` | Email delivery, encrypted outbox payloads, outbox worker and Mailgun webhooks |
| `faculty/` | Attendance orchestration/reporting; `attendance/` owns bounded file/row parsing, exact identity and import validation; responsibilities, student management and examinations; `assessment_roster.py` owns current participation and saved marks projections |
| `invitations/` | Platform/admin/student invitations, invitation abuse controls and account acceptance/recovery |
| `knowledge/` | Document ingestion, storage, extraction, chunking, embeddings, retrieval, vector search and public knowledge policy |
| `platform/` | Institutions, organizations, tenancy and staff/faculty onboarding |
| `students/` | Student context, academic profiles/experience, attendance, results, class registrations, notices, notifications and resources |

Import from the feature package explicitly:

```python
from app.services.faculty import faculty_attendance
from app.services.auth.authorization import effective_authorization
```

Package `__init__.py` files do not eagerly import services. Keep imports explicit
and retain existing function-local imports where they defer circular dependencies.
Use the full module path in mock targets as well, for example
`patch("app.services.faculty.faculty_attendance.get_admin_client")`.

`auth/student_registration.py` creates a student account;
`students/student_registrations.py` manages class registrations;
`students/subject_assignments.py` authorizes and creates subject memberships;
`invitations/student_registration_invitations.py` sends signup invitations.

`students/student_academic_experience.py` resolves student ownership and
orchestrates read-only projections in `students/academic_experience/`.
Attendance and published scores retain ended subject history; upcoming
assessments require current subject participation.

Add new services to the appropriate feature package. The services root contains
only this guide and its package marker. Historical phase reports and evidence
snapshots may refer to the former flat module paths; use Git history to inspect
those versions.
