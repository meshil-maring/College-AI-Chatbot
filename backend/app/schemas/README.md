# Backend schemas

Follow the shared [backend structure rules](../../STRUCTURE.md).

Pydantic request, response and domain models are grouped by feature, matching
the API and service layout. Model definitions, validators, field names, defaults
and serialization rules stay in their existing modules.

| Package | Schema modules |
| --- | --- |
| `academics/` | `academic_setup.py` |
| `admin/` | `admin.py`, `admin_dashboard.py`, `admin_memberships.py` |
| `ai/` | `chat.py`, `chat_response.py`, `citation.py`, `conversation.py`, `generation.py`, `personalization.py`, `personalized_context.py`, `session.py` |
| `auth/` | `auth.py`, `student_auth.py`, `users.py`, `phase81.py` (scoped permission and assignment requests) |
| `faculty/` | `faculty_attendance.py`, `faculty_responsibilities.py`, `faculty_tests.py` |
| `invitations/` | `admin_invitations.py`, `super_admin_registration.py` |
| `knowledge/` | `ingestion.py`, `retrieval.py` |
| `platform/` | `platform.py`, `tenancy.py` |
| `students/` | `student_academic_context.py`, `student_academic_experience.py`, `student_attendance.py`, `student_notices.py`, `student_notifications.py`, `student_profile.py`, `student_registrations.py`, `student_resources.py`, `student_results.py` |

Import models from their owning modules explicitly:

```python
from app.schemas.auth.auth import AuthRequest
from app.schemas.ai.generation import RetrievedChunk
from app.schemas.students.student_registrations import StudentRegistrationCreate
```

Package `__init__.py` files do not eagerly import models. This keeps feature
boundaries visible and avoids circular imports or loading unrelated contracts.
Add new models to their owning feature rather than to the schemas root.

Shared contracts have one implementation. For example, personalized AI context
imports the student academic context model, and class registration imports the
faculty roster input model. Reuse those models instead of copying them into
another package.

`ai/generation.py` defines the generated-answer `AIResponse`;
`ai/conversation.py` defines the persisted-response `AIResponse`. Their existing
module ownership keeps these distinct contracts unambiguous.

API routes, services, repositories and tests use the same canonical model paths.
When changing a contract, check validation/serialization and the resulting
OpenAPI request/response schemas. Historical phase reports and evidence snapshots
may refer to former flat paths; Git history retains those versions.
