# Backend services

Follow the shared [backend structure rules](../../STRUCTURE.md).

`academics/semester_registration.py` owns curriculum option groups, administrator
section assignment and student whole-option registration. It preserves exact
institution grants, account approval and ownership; SQL commands atomically
enroll required and selected subjects and check offerings and capacity.

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
| `knowledge/` | Document pipeline and audience-aware retrieval; `resources/` owns drafts, review, staged uploads, legacy adapters and answer/history policy |
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

`ai/chat_support/resource_scope.py` resolves immutable conversation context,
rechecks resource eligibility, binds answer policy and validates restored
provenance. Ordinary conversations retain their existing institution-wide scope.

`knowledge/resources/operations.py` coordinates atomic SQL readers/writers and
safe error mapping. `uploads.py` validates files and reuses the existing indexing
pipeline without publishing. `legacy.py` stages old admin upload routes;
`policy.py` verifies answer/history provenance, and `public_chat.py` rechecks the
public corpus around the existing stateless processor. Schema absence fails closed.

`knowledge/evidence_selection.py` expands metadata-heavy retrieval within the
same authorized document version. It retains a complete authority/cover passage
and returns substantive sections within the original context limit. Generation
treats document instructions as data and preserves sample/draft qualifications.

`ai/turns/workflow.py` claims stable signed-in requests before provider work and
replays completed receipts. `operations.py` owns safe RPC error translation and
atomic completion payloads. `chat_support/answers.py` retains legacy persistence
for unkeyed callers; keyed turns persist all answer records in one SQL transaction.

`ai/chat_support/history_sources.py` batches citation restoration for history API
reads. A policy change redacts the affected answer and dependent tail; unavailable
resource context also removes its questions. Internal generation history skips
presentation enrichment. Missing or failed citation schema returns a safe 503.

`ai/generation_format.py` validates the provider's separate Markdown answer and
selected source positions. Quotes and provenance come from the authorized
retrieved chunks. The provider request uses a strict JSON schema with source
numbers constrained to those chunks and matching labels in the prompt. The
configured model must support OpenRouter's [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).
Unknown positions, missing evidence and malformed/truncated
JSON fail safely; retrieved context is never automatically presented as cited.
`generation_prompt.py` renders context shared by the provider and diagnostics.
The stateless public projector retains its internal-marker compatibility path;
the generation service supplies validated markers and projection strips them.
Signed-in answers use explicit references directly. Source-card quotes use the
same whitespace normalization for live and restored PDF evidence.
`generation_qualification.py` preserves explicit sample/nonofficial authority
declarations for the exact cited document version. It adds a deterministic
caveat and cites the declaration itself, even when the model selects only a
substantive section. Ordinary mentions of drafts do not trigger that behavior.
