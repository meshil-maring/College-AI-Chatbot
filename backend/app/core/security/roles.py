"""Security roles responsibilities."""




SUPPORTED_ROLES: tuple[str, ...] = (
    "super_admin",
    "admin",
    "staff",
    "faculty",
    "student",
)


_ROLE_PRECEDENCE: dict[str, int] = {
    role: index for index, role in enumerate(SUPPORTED_ROLES)
}


def resolve_primary_role(roles: list[str] | tuple[str, ...] | None) -> str | None:
    """Resolve the canonical primary role from the server-side role list.

    Returns the highest-precedence SUPPORTED role, or None when the account
    holds no supported role (unknown/unsupported roles are never reported —
    the caller treats None as "no privileged UI").
    """
    if not roles:
        return None
    supported = [
        _ROLE_PRECEDENCE[role]
        for role in roles
        if role in _ROLE_PRECEDENCE
    ]
    if not supported:
        return None
    return SUPPORTED_ROLES[min(supported)]
