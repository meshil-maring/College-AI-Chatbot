# Backend API routers

Follow the shared [backend structure rules](../../STRUCTURE.md).

Routers are grouped by feature, matching the organization of
[backend services](../services/README.md). Moving a router does not change its
URL prefix, permissions or request/response models.

| Package | Router modules |
| --- | --- |
| `academics/` | `academic_setup.py`, `academic_packages.py` (curricula, packages, class setup, assignment and requests) |
| `admin/` | `admin.py` assembles feature routers; see the [Admin API guide](admin/README.md) |
| `ai/` | `conversations.py` |
| `auth/` | Core auth feature routers, student login, registration and development tools; see the [Auth API guide](auth/README.md) |
| `email/` | `mailgun_webhooks.py` |
| `faculty/` | `faculty.py`, `faculty_tests.py`, `registrations.py`, and shared `dependencies.py` |
| `invitations/` | `admin_invitations.py`, `super_admin_registration.py` |
| `knowledge/` | `ingestion.py` |
| `platform/` | `institutions.py`, `organizations.py`, `platform.py` |
| `students/` | `students.py`, `student_notifications.py` |

`app/main.py` creates the application and uses `core/application_routes.py` to
register feature routers explicitly. The faculty router continues to include
the faculty examinations router. `auth/identity.py` owns identity bootstrap;
`ai/public_contract.py` owns the public chat response documentation.

```python
from app.api.faculty.faculty import router as faculty_router
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
