# Backend services

Follow the shared [backend structure rules](../../STRUCTURE.md).

Services are grouped by feature. API routers call these modules; repositories
continue to own database access and schemas continue to own request/response types.

| Package | Related services |
| --- | --- |
| `academics/` | Export-aligned foundation, dated-semester, course, curriculum-link, offering and section setup |
| `admin/` | Student account approvals, dashboard, documents, FAQs, memberships and notices |
| `ai/` | Authenticated/public chat, conversation history and intent, context, generation, privacy safeguards and query rewriting |
| `auth/` | Sign-in, sessions, account registration, authorization, RBAC and shared request-abuse controls |
| `email/` | Email delivery, encrypted outbox payloads, outbox worker and Mailgun webhooks |
| `invitations/` | Platform/admin invitations, invitation abuse controls and account acceptance/recovery |
| `knowledge/` | Document ingestion, storage, extraction, chunking, embeddings, retrieval, vector search and public knowledge policy |
| `platform/` | Institutions, organizations, tenancy and staff/faculty onboarding |
| `students/` | Account identity profiles, notices, notifications and resources |

Import from the feature package explicitly:

```python
from app.services.admin import admin_academics
from app.services.auth.authorization import effective_authorization
```

Package `__init__.py` files do not eagerly import services. Keep imports explicit
and retain existing function-local imports where they defer circular dependencies.
Use the full module path in mock targets as well, for example
`patch("app.services.admin.admin_academics.get_admin_client")`.

`auth/student_registration.py` creates a student account;
`admin/admin_academics.py` retains its established import path for account
approval and atomic role provisioning. It contains no academic setup workflow.
`auth/authorization.py` coordinates account scope resolution with
`scope_types.py`, `scope_policy.py` and `scope_lifecycle.py`.

`academics/academic_setup.py` coordinates the eight export-aligned entities.
`academics/authorization.py` enforces exact institution-admin permission provenance
and tenant/organization lifecycle. `parent_validation.py` checks active ancestry,
semester dates and matching curriculum links. `database_errors.py` maps database
errors to safe responses. Repositories derive tenant scope through parent joins;
all writes use the atomic, audited `manage_academic_master_record` RPC.
Attendance, results, academic packages, enrollment and teaching workflows remain
retired. Chat continues to refuse private academic record requests.

`academics/academic_structure.py` coordinates the additive workspace entities.
It reuses exact scoped authorization and safe database-error translation, and
delegates writes to `manage_academic_structure_record`. Database constraints and
triggers enforce publication, immutable cohort assignments, active ancestry and
deactivation guards. The service never fabricates enrolled student counts.

Add new services to the appropriate feature package. The services root contains
only this guide and its package marker. Historical phase reports and evidence
snapshots may refer to the former flat module paths; use Git history to inspect
those versions.
