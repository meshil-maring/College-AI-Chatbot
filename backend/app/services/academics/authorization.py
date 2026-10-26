"""Shared exact institution-admin scope and active organization checks."""

from app.core.errors import AppError
from app.core.permissions import permission_matches
from app.core.security.scoped_permissions import permissions_for_scope
from app.repositories.academics import academic_setup as repository


def scope(user):
    tenant = user.get("institution_id")
    if not tenant or not user.get("user_id"):
        raise AppError("Institution administrator access required", 403, "FORBIDDEN")
    permissions = permissions_for_scope(
        user, "institution", tenant, allowed_roles={"admin"}
    )
    return str(tenant), permissions


def allowed(permissions, entity, action):
    resource = entity.permission_resource
    return permission_matches(permissions, f"{resource}.{action}")


def require(permissions, entity, action):
    if not allowed(permissions, entity, action):
        raise AppError("You do not have permission to perform this action", 403, "FORBIDDEN")


def validated_scope_permissions(client, user, institution_id):
    """Match the new writer's parent lifecycle and organization grant checks."""
    institution = repository.get_institution_lifecycle(client, institution_id)
    if (
        not institution or institution.get("status") != "active"
        or institution.get("is_active") is not True
    ):
        raise AppError("This institution is not active", 403, "TENANT_INACTIVE")
    organization_id = institution.get("organization_id")
    organization = (
        repository.get_organization_lifecycle(client, str(organization_id))
        if organization_id else None
    )
    if not organization or organization.get("status") != "active":
        raise AppError("This organization is not active", 403, "ORGANIZATION_INACTIVE")
    # A permission on an inconsistent organization grant cannot authorize reads
    # when the atomic writer would reject that same grant.
    scoped_user = {
        **user,
        "role_assignments": [
            grant for grant in user.get("role_assignments") or []
            if str(grant.get("scope_organization_id")) == str(organization_id)
        ],
    }
    return permissions_for_scope(
        scoped_user, "institution", institution_id, allowed_roles={"admin"}
    )


