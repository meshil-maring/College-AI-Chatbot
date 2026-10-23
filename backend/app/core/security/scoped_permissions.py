"""Evaluate permission provenance for one server-selected role scope."""


def permissions_for_scope(user, scope_type, scope_id, *, allowed_roles=None):
    """Aggregate exact-scope grants only with resolved permission provenance."""
    if user.get("scoped_permissions_resolved") is not True:
        return []
    if scope_type not in {"platform", "organization", "institution"}:
        return []
    if scope_type != "platform" and scope_id is None:
        return []
    roles = set(user.get("roles") or ())
    if allowed_roles is not None:
        roles.intersection_update(allowed_roles)
    grants = [
        grant
        for grant in user.get("role_assignments") or ()
        if grant.get("is_active", True)
        and grant.get("role") in roles
        and grant.get("scope_type") == scope_type
        and str(grant.get("scope_id")) == str(scope_id)
    ]
    permissions = {
        code
        for grant in grants
        for code in grant.get("permissions") or ()
        if isinstance(code, str)
    }
    if scope_type == "institution" and any(g["role"] == "staff" for g in grants):
        permissions.update(
            grant["permission"]
            for grant in user.get("direct_permission_grants") or ()
            if str(grant.get("institution_id")) == str(scope_id)
            and isinstance(grant.get("permission"), str)
        )
    return sorted(permissions)


def primary_scope_permissions(user, primary_role):
    """Ambiguous or absent primary-role scope never supplies permissions."""
    scopes = {
        (grant.get("scope_type"), grant.get("scope_id"))
        for grant in user.get("role_assignments") or ()
        if grant.get("is_active", True) and grant.get("role") == primary_role
    }
    if len(scopes) != 1:
        return []
    scope_type, scope_id = next(iter(scopes))
    return permissions_for_scope(user, scope_type, scope_id)
