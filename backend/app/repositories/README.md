# Backend repositories

Follow the shared [backend structure rules](../../STRUCTURE.md).

Database access modules are grouped by feature, following the API, service and
schema layout. Existing queries, tenant filters, RPC calls and return values
remain in their owning modules.

| Package | Repository modules |
| --- | --- |
| `academics/` | `attendance.py`, `results.py` |
| `admin/` | `admin_academics.py`, `admin_audit.py`, `admin_knowledge.py`, `admin_memberships.py` |
| `ai/` | `ai_response.py`, `conversation.py`, `message.py`, `message_citation.py`, `personalization.py` |
| `email/` | `email_outbox.py` |
| `invitations/` | `platform_admin_invitations.py` |
| `knowledge/` | `embeddings.py`, `ingestion.py`, `public_knowledge.py`, `retrieval_operation.py`, `vector_search.py` |
| `platform/` | `platform_institutions.py`, `tenancy.py` |
| `students/` | `student_academic_experience.py`, `student_dashboard.py`, `student_notifications.py` |
| `shared/` | `query_pages.py` (shared row reads and pagination) |

Import repositories and helpers explicitly:

```python
from app.repositories.admin import admin_academics as academics_repo
from app.repositories.shared.query_pages import read_all
```

Package `__init__.py` files do not eagerly import repositories. Add database
operations to the owning feature and reuse shared pagination helpers rather
than copying them. Keep business orchestration in services and authorization
policy in the existing service/core layers.

Callers pass database clients to repository operations. Preserve tenant scope,
query projections and pagination behavior when extending these operations.
Tests and mock targets use the same canonical module paths as application code.

Historical phase reports and evidence snapshots may refer to former flat paths;
Git history retains those versions.
