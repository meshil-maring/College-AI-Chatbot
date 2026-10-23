# Core application infrastructure

Follow the shared [backend structure rules](../../STRUCTURE.md).

| Path | Responsibility |
| --- | --- |
| `errors.py` | Application errors and their HTTP response handler |
| `permissions.py` | Static permission catalog, role defaults and permission matching |
| `security/` | Token verification, authenticated identity and authorization dependencies |
| `startup_validation/` | Configuration checks, safe reports and startup enforcement |
| `application.py` | Application creation, middleware and safe HTTP error handlers |
| `application_routes.py` | Feature router registration with unchanged public paths |
| `operational_routes.py` | Root, health and read-only readiness endpoints |

## Security

| Module | Responsibility |
| --- | --- |
| `security/__init__.py` | Public exports used by API routers, services and tests |
| `security/tokens.py` | JWT verification, JWKS client cache, issuer/audience checks and safe verification errors |
| `security/identity.py` | Bearer header handling, application user projection and public conversation identity |
| `security/roles.py` | Supported roles and primary-role precedence |
| `security/tenancy.py` | Tenant UUID resolution, scope selection and row guards |
| `security/permissions.py` | Resolved permission checks and permission dependencies |
| `security/scoped_permissions.py` | Permission provenance for the selected role and scope |
| `security/dependencies.py` | Role, institution and platform Super Admin dependencies |

Existing imports remain valid, for example:

```python
from app.core.security import get_current_user, require_institution_roles
```

The public exports reference the implementation functions directly, preserving
FastAPI dependency identity and dependency overrides. JWT verification is called
through the `tokens` module; tests patch
`app.core.security.tokens.verify_jwt` or its JWKS client provider.
There is one JWKS cache and one `user_tenant_id` implementation.

Keep the identity module independent of service initialization. The existing
database and authorization-service imports inside dependency functions defer
circular dependencies. New permission codes belong in the static catalog at
`core/permissions.py`; runtime enforcement belongs in `security/permissions.py`.
The frontend RBAC generator reads `security/roles.py` directly without loading
application settings.

## Startup validation

| Module | Responsibility |
| --- | --- |
| `startup_validation/__init__.py` | Public check model, collection, reporting and startup entry points |
| `startup_validation/models.py` | Immutable `ConfigurationCheck` results |
| `startup_validation/helpers.py` | Value-free presence checks and URL shape validation |
| `startup_validation/required.py` | Required Supabase, AI and storage configuration |
| `startup_validation/endpoints.py` | Production endpoint/issuer checks and CORS origins |
| `startup_validation/email.py` | Mailgun configuration, outbox encryption key and email URLs |
| `startup_validation/runtime.py` | Development flags, debug mode, allowed hosts and AI provider selection |
| `startup_validation/runner.py` | Ordered collection, safe summaries and startup enforcement |

Existing imports from `app.core.startup_validation` remain valid. The coordinator
keeps the established check order: required configuration, endpoints/CORS, email,
then runtime checks. Local development/test environments warn and continue;
other environments refuse startup when a check fails.

Checks inspect local configuration only. They do not construct provider clients
or make network requests. Details and summaries name configuration requirements
without exposing configured values. Add new checks to the appropriate group and
retain these reporting and environment boundaries.
## Scoped permission provenance

`security/scoped_permissions.py` aggregates role and staff permission grants for
one server-selected scope. The identity projection retains each role's permission
codes; institution dependencies recalculate permissions for their allowed roles
and exact institution. The aggregate permission list must not authorize a
different tenant or a role outside that operation's allowed roles.
