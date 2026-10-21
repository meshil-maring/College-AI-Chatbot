# Admin API

`admin.py` assembles the feature routers. It owns the shared `admin` tag and
permission dependency; it contains no endpoint handlers.

| Module | Responsibility |
| --- | --- |
| `dependencies.py` | Permission policy map, fail-closed authorization, Admin/Staff role dependencies and feature router factory |
| `common.py` | Institution/row/student guards, database client access and audit recording |
| `overview.py` | Admin identity and dashboard |
| `memberships.py` | Staff/faculty onboarding decisions, roster, activation and invitation resend |
| `knowledge_sources.py` | Knowledge source creation, listing and updates |
| `documents.py` | Document listing, upload, versions and deletion |
| `faqs.py` | FAQ management and publication |
| `notices.py` | Notice management |
| `students.py` | Student management and pending approval/rejection |
| `results.py` | Results, CSV uploads and test results |
| `attendance.py` | Student attendance management |
| `audit.py` | Audit log queries |
| `permissions.py` | Staff permission delegation |
| `faculty.py` | Faculty teaching assignments and responsibilities |
| `student_workspace.py` | Sections, rosters, profiles, registration history, batches and invitations |

## Shared boundaries

Each feature creates its router with `dependencies.create_feature_router()`.
The factory gives leaf routes their `/admin` prefix so permission checks see the
same route templates, including `{student_id}` and other placeholders, when
routers are nested. Do not add another `/admin` prefix when including a feature.

`admin.py` applies `_authorize_admin_endpoint` to every included feature. The
central map requires an explicit permission policy for each method/path;
missing policies deny access. Endpoint role dependencies reuse the same `_ADMIN`
and `_APPROVAL` objects from `dependencies.py`.

Tenant guards and audit writes go through `common`. Student approval retains its
existing service-owned provisioning/audit workflow. Features call the existing
services and repositories; this split does not change their transaction behavior.
The Faculty API also uses `common.record_audit` without importing an admin router.

## Adding an endpoint

1. Add the handler to its feature module, using `_ADMIN` or `_APPROVAL` as appropriate.
2. Add its method and full `/admin/...` route template to `_ADMIN_ROUTE_PERMISSIONS`.
3. Retain institution/row checks and audit recording for the operation.
4. For a new feature, use `create_feature_router()` and include it in `admin.py`.
5. Check permission coverage and endpoint behavior. Keep literal student paths
   such as `/students/pending` before `/students/{student_id}`.

Tests patch the module that owns a dependency: services/repositories directly,
or `app.api.admin.common.get_admin_client` and
`app.api.admin.common.record_audit` for shared API helpers. Patches no longer
target implementation attributes on the router assembler.
