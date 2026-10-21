"""Public security API. Imports expose the shared dependency objects directly."""

from app.core.security.tokens import verify_jwt
from app.core.security.roles import SUPPORTED_ROLES, resolve_primary_role
from app.core.security.identity import PUBLIC_USER_ID, get_current_user
from app.core.security.tenancy import user_tenant_id, scope_tenant, assert_tenant_object
from app.core.security.permissions import (
    has_permission,
    authorize_permissions,
    require_permission,
    require_permissions,
)
from app.core.security.dependencies import (
    require_roles,
    require_institution_roles,
    require_institution_permission,
    require_super_admin,
)

__all__ = [
    "verify_jwt",
    "SUPPORTED_ROLES",
    "resolve_primary_role",
    "PUBLIC_USER_ID",
    "get_current_user",
    "user_tenant_id",
    "scope_tenant",
    "assert_tenant_object",
    "has_permission",
    "authorize_permissions",
    "require_permission",
    "require_permissions",
    "require_roles",
    "require_institution_roles",
    "require_institution_permission",
    "require_super_admin",
]
