# Backend repositories

Follow the shared [backend structure rules](../../STRUCTURE.md).

`academics/semester_registration.py` reads tenant-filtered assignment data and
calls audited option-group, section-assignment and student-registration RPCs.
Student identity is always resolved from the authenticated actor by the database.

Database access modules are grouped by feature, following the API, service and
schema layout. Existing queries, tenant filters, RPC calls and return values
remain in their owning modules.

| Package | Repository modules |
| --- | --- |
| `academics/` | `academic_setup.py`: existing tenant-scoped joins/writer; `academic_structure.py`: tenant-filtered workspace records, audit activity and the additive writer |
| `admin/` | `admin_academics.py` (student account identity and approvals), `admin_audit.py`, `admin_knowledge.py`, `admin_memberships.py` |
| `ai/` | `ai_response.py`, `conversation.py`, `message.py`, `message_citation.py`, `chat_turns.py` (service-only durable turn RPCs) |
| `email/` | `email_outbox.py` |
| `invitations/` | `platform_admin_invitations.py` |
| `knowledge/` | `embeddings.py`, `ingestion.py`, `public_knowledge.py`, `retrieval_operation.py`, `vector_search.py`; `resources.py` calls scoped revision/library and audience-search RPCs |
| `platform/` | `platform_institutions.py`, `tenancy.py` |
| `students/` | `student_content.py` (tenant-scoped notices and resources), `student_notifications.py` |
| `shared/` | `query_pages.py` (shared row reads and pagination) |

Import repositories and helpers explicitly:

```python
from app.repositories.admin import admin_academics as identity_repo
from app.repositories.shared.query_pages import read_all
```

Package `__init__.py` files do not eagerly import repositories. Add database
operations to the owning feature and reuse shared pagination helpers rather
than copying them. Keep business orchestration in services and authorization
policy in the existing service/core layers.

Callers pass database clients to repository operations. Preserve tenant scope,
query projections and pagination behavior when extending these operations.
`academics/academic_setup.py` deletes unused departments/programs exclusively
through their atomic `delete_unused_academic_department` and
`delete_unused_academic_program` RPCs with server-derived actor/tenant.
Calendar and class-section deletes call `delete_unused_academic_calendar_record`
with a server-selected entity. Section storage stays in `academic_structure.py`;
dated years/semesters stay in `academic_setup.py`. No table DELETE is issued here.
Tests and mock targets use the same canonical module paths as application code.
Conversation reads include the stored resource/source institution; inserts only
write those columns when creating a resource-scoped conversation. Database
triggers forbid subsequent scope or owner reassignment.

`ai/message_citation.py` reads history cards through the owner-scoped
`read_conversation_citations` RPC. It never reconstructs cards from browser input
or from retrieved context without persisted citations.

The retained `admin_academics.py` import path supports login, account
registration and approvals. Its projections contain identity fields only;
academic master references, rosters, results and attendance queries are removed.

Historical phase reports and evidence snapshots may refer to former flat paths;
Git history retains those versions.
