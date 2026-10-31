# Backend API routers

Follow the shared [backend structure rules](../../STRUCTURE.md).

Routers are grouped by feature, matching the organization of
[backend services](../services/README.md). Moving a router does not change its
URL prefix, permissions or request/response models.

| Package | Router modules |
| --- | --- |
| `academics/` | `academic_setup.py`: existing eight-entity API; `academic_structure.py`: versioned curricula, program semesters, cohorts, class sections and offerings |
| `admin/` | `admin.py` assembles feature routers; see the [Admin API guide](admin/README.md) |
| `ai/` | `conversations.py`, `chat_turns.py` (authenticated read-only recovery status) |
| `auth/` | Core auth feature routers, student login, registration and development tools; see the [Auth API guide](auth/README.md) |
| `email/` | `mailgun_webhooks.py` |
| `invitations/` | `admin_invitations.py`, `super_admin_registration.py` |
| `knowledge/` | `ingestion.py`; `resources.py` shared library/draft/review; `resource_uploads.py` staged uploads and indexing retries |
| `platform/` | `institutions.py`, `organizations.py`; `platform.py` assembles institution, invitation and audit routes with shared `dependencies.py` |
| `students/` | `students.py`, `student_notifications.py` |

`app/main.py` creates the application and uses `core/application_routes.py` to
register feature routers explicitly. The replacement academic router enforces
institution-admin scope and entity permissions independently. Faculty teaching
routers remain retired. `auth/identity.py` owns account identity bootstrap;
`ai/public_contract.py` owns the public chat response documentation.

`DELETE /admin/academic-setup/departments/{record_id}` deletes only unused
departments. It requires the exact institution-admin department-management grant;
active or inactive dependencies return `409 DEPARTMENT_IN_USE`.
`DELETE /admin/academic-setup/programs/{record_id}` uses the same grant and
returns `409 PROGRAM_IN_USE` for linked records.
DELETE on `/admin/academic-setup/academic_years/{record_id}` and
`/admin/academic-setup/semesters/{record_id}` requires their respective manage
grants. `/admin/academic-structure/academic_sections/{record_id}` requires
`courses.manage`. All require exact institution-admin scope. Current periods
return `409 ACADEMIC_CURRENT_PERIOD`; links return entity-specific `*_IN_USE`
conflicts. Offering-owned legacy sections retain their existing contract.

`academics/semester_registration.py` exposes administrator option groups and
section assignment under `/admin/academic-registration`, plus owner-scoped reads
and completion under `/students/me/semester-registrations`. It uses independent
student registration grants and never restores retired package routes.

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

The [learning-resource contract](../../../docs/architecture/ai-chatbot/API.md)
defines the shared `/knowledge` endpoints. These use institution-role dependencies
and service-only SQL writers that recheck exact grants, ownership and review state.
