# Backend API routers

Follow the shared [backend structure rules](../../STRUCTURE.md).

Routers are grouped by feature, matching the organization of
[backend services](../services/README.md). Moving a router does not change its
URL prefix, permissions or request/response models.

| Package | Router modules |
| --- | --- |
| `academics/` | `academic_setup.py`: institution-admin catalogue and writes for the eight export-aligned setup entities |
| `admin/` | `admin.py` assembles feature routers; see the [Admin API guide](admin/README.md) |
| `ai/` | `conversations.py` |
| `auth/` | Core auth feature routers, student login, registration and development tools; see the [Auth API guide](auth/README.md) |
| `email/` | `mailgun_webhooks.py` |
| `invitations/` | `admin_invitations.py`, `super_admin_registration.py` |
| `knowledge/` | `ingestion.py` |
| `platform/` | `institutions.py`, `organizations.py`; `platform.py` assembles institution, invitation and audit routes with shared `dependencies.py` |
| `students/` | `students.py`, `student_notifications.py` |

`app/main.py` creates the application and uses `core/application_routes.py` to
register feature routers explicitly. The replacement academic router enforces
institution-admin scope and entity permissions independently. Faculty teaching
routers remain retired. `auth/identity.py` owns account identity bootstrap;
`ai/public_contract.py` owns the public chat response documentation.

Platform leaf routers carry `/platform` on their own route templates, just as
admin leaves carry `/admin`. The central permission dependencies inspect these
templates and deny any operation without an explicit method/path policy.

```python
from app.api.admin.admin import router as admin_router
from app.api.students import students as students_api
```

Use full module paths for test patches, for example
`patch("app.api.students.students.student_data.get_own_profile")`.
Package `__init__.py` files do not eagerly import routers. Keep existing
function-local imports where they defer dependencies.

Add new routers to the appropriate feature package and register them in
`app/main.py` or their parent router. Keep endpoint orchestration here,
business logic in services, and database access in repositories.
Historical phase reports and evidence snapshots may refer to the previous
flat module paths; Git history retains those versions.
