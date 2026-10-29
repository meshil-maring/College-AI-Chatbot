# Backend schemas

Follow the shared [backend structure rules](../../STRUCTURE.md).

Pydantic request, response and domain models are grouped by feature, matching
the API and service layout. Model definitions, validators, field names, defaults
and serialization rules stay in their existing modules.

| Package | Schema modules |
| --- | --- |
| `academics/` | `academic_setup.py`: existing contracts; `academic_structure.py`: strict create/update contracts for program semesters, curricula, cohorts, academic sections and offerings |
| `admin/` | `admin.py`, `admin_dashboard.py`, `admin_memberships.py` |
| `ai/` | `chat.py`, `chat_turns.py`, `chat_response.py`, `citation.py`, `conversation.py`, `generation.py`, `session.py` |
| `auth/` | `auth.py`, `student_auth.py`, `users.py`, `phase81.py` (scoped permission requests) |
| `invitations/` | `admin_invitations.py`, `super_admin_registration.py` |
| `knowledge/` | `ingestion.py`, `retrieval.py`; `resources.py` defines strict audience/draft/review inputs and safe resource/revision/file projections |
| `platform/` | `platform.py`, `tenancy.py` |
| `students/` | `student_notices.py`, `student_notifications.py`, `student_profile.py`, `student_resources.py` |

Import models from their owning modules explicitly:

```python
from app.schemas.auth.auth import AuthRequest
from app.schemas.ai.generation import RetrievedChunk
from app.schemas.students.student_profile import StudentProfile
```

Package `__init__.py` files do not eagerly import models. This keeps feature
boundaries visible and avoids circular imports or loading unrelated contracts.
Add new models to their owning feature rather than to the schemas root.

Shared contracts have one implementation. Reuse the owning feature's models
instead of copying them into another package. Student profiles contain account
identity fields. Replacement setup contracts distinguish degree programs from
subjects; participation and teaching schemas remain retired.

`ai/generation.py` defines the generated-answer `AIResponse` and preserves
canonical imports for prompt inputs owned by `ai/generation_context.py`.
Generated multiline answers retain Markdown line breaks and indentation;
`ai/conversation.py` defines the persisted-response `AIResponse`. Their existing
module ownership keeps these distinct contracts unambiguous.
`ai/resource_context.py` defines the safe source/title/availability contract used
by chat responses and conversation summaries; internal policy stamps stay private.
`MessageSummary.sources` reuses `StructuredSource` for restored citation cards;
empty source lists preserve uncited and legacy message compatibility.

API routes, services, repositories and tests use the same canonical model paths.
When changing a contract, check validation/serialization and the resulting
OpenAPI request/response schemas. Historical phase reports and evidence snapshots
may refer to former flat paths; Git history retains those versions.
