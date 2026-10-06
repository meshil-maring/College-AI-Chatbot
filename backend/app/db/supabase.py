import threading

from supabase import Client, create_client

from app.config import settings


def create_supabase_client() -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


_admin_client: Client | None = None
_admin_client_config: tuple[str, str] | None = None
_admin_client_lock = threading.Lock()


def get_admin_client() -> Client:
    """Service-role client — bypasses RLS. Use only for server-side operations.

    Creating a Supabase client builds an entirely new HTTP session stack, which
    measurably costs several hundred milliseconds per call and happens many
    times per chat request. The admin client is therefore created once per
    (url, secret key) configuration and reused. supabase-py clients are
    thread-safe for query/RPC execution, so one shared instance is safe for
    concurrent requests. A configuration change (e.g. tests replacing keys)
    produces a fresh client because the cache is keyed by configuration.
    """
    global _admin_client, _admin_client_config
    config = (settings.supabase_url, settings.supabase_secret_key)
    with _admin_client_lock:
        if _admin_client is None or _admin_client_config != config:
            _admin_client = create_client(*config)
            _admin_client_config = config
        return _admin_client


async def get_user_by_auth_id(
    auth_user_id: str,
    *,
    include_permissions: bool = False,
) -> dict | None:
    """Return the application identity and authoritative scoped role grants.

    ``user_roles.scope_*`` is the authority for non-student role scope.  The
    students relation remains available only as the legitimate student-profile
    tenant source; it is never used to manufacture scope for an admin, staff or
    faculty grant.
    """
    client = get_admin_client()
    role_projection = (
        "user_roles(scope_type, scope_id, scope_organization_id, "
        "roles(name, is_active, "
        "role_permissions(permissions(code, is_active, scope)))), "
        "user_permission_grants!user_permission_grants_user_id_fkey("
        "institution_id, revoked_at, "
        "permissions(code, is_active))"
        if include_permissions
        else "user_roles(scope_type, scope_id, scope_organization_id, "
        "roles(name, is_active))"
    )
    response = (
        client.table("users")
        .select(
            "user_id:id, auth_user_id, email, status, "
            f"{role_projection}, "
            "students(institution_id)"
        )
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        return None
    row = response.data
    role_assignments = []
    effective_permissions: set[str] = set()
    direct_permission_grants: list[dict] = []
    for grant in row.get("user_roles") or []:
        role = grant.get("roles")
        if not isinstance(role, dict) or not role.get("is_active", True):
            continue
        role_name = role.get("name")
        if not role_name:
            continue
        if include_permissions:
            for role_permission in role.get("role_permissions") or []:
                if not isinstance(role_permission, dict):
                    continue
                permission = role_permission.get("permissions")
                permission_scope = (
                    permission.get("scope") if isinstance(permission, dict) else None
                )
                role_scope = grant.get("scope_type")
                permission_scope_matches = (
                    permission_scope in {None, "global", "user", role_scope}
                    or (
                        role_scope == "platform"
                        and permission_scope in {"institution", "organization"}
                    )
                )
                if (
                    isinstance(permission, dict)
                    and permission.get("is_active", True)
                    and isinstance(permission.get("code"), str)
                    and permission_scope_matches
                ):
                    effective_permissions.add(permission["code"])
        role_assignments.append(
            {
                "role": role_name,
                "scope_type": grant.get("scope_type"),
                "scope_id": grant.get("scope_id"),
                "scope_organization_id": grant.get("scope_organization_id"),
                "is_active": True,
            }
        )
    roles = [grant["role"] for grant in role_assignments]
    student_links = row.get("students") or []
    # PostgREST embeds the students relation as a single object when the FK is
    # detected as one-to-one, and as a list otherwise. Handle both shapes.
    if isinstance(student_links, dict):
        institution_id = student_links.get("institution_id")
    elif student_links:
        institution_id = student_links[0].get("institution_id")
    else:
        institution_id = None
    result = {
        "user_id": row["user_id"],
        "auth_user_id": row["auth_user_id"],
        "email": row["email"],
        "status": row.get("status"),
        "roles": roles,
        "institution_id": institution_id,
        "student_institution_id": institution_id,
        "role_assignments": role_assignments,
    }
    if include_permissions:
        result["effective_permissions"] = sorted(effective_permissions)
        for grant in row.get("user_permission_grants") or []:
            permission = grant.get("permissions")
            if (
                grant.get("revoked_at") is None
                and isinstance(permission, dict)
                and permission.get("is_active", True)
                and isinstance(permission.get("code"), str)
            ):
                direct_permission_grants.append({
                    "institution_id": grant.get("institution_id"),
                    "permission": permission["code"],
                })
        result["direct_permission_grants"] = direct_permission_grants
        result["permissions_resolved"] = True
    return result


async def get_super_admin_authorization(auth_user_id: str) -> dict | None:
    """Read the fresh account lifecycle and platform grant for one Auth user.

    This intentionally remains separate from ``get_user_by_auth_id`` so the
    locked general authentication projection and return contract stay stable.
    Platform authorization pays for this narrow second read to ensure that a
    revocation takes effect on the very next protected request.
    """
    client = get_admin_client()
    response = (
        client.table("users")
        .select("status, user_roles(scope_type, roles(name, is_active))")
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        return None
    row = response.data
    has_platform_grant = any(
        grant.get("scope_type") == "platform"
        and isinstance(grant.get("roles"), dict)
        and grant["roles"].get("name") == "super_admin"
        and grant["roles"].get("is_active", True)
        for grant in (row.get("user_roles") or [])
    )
    return {
        "status": row.get("status"),
        "has_platform_grant": has_platform_grant,
    }


async def get_sign_in_context(auth_user_id: str) -> dict | None:
    """Phase 6.13.6 — resolve the sign-in status context for an auth account.

    Additive sibling of :func:`get_user_by_auth_id` — the locked authentication
    projection and return contract are UNCHANGED; this narrower read fetches
    only the status fields the Phase 6.13.6 sign-in guard needs:

        * ``public.users.status``         — account lifecycle (active/inactive/deactivated)
        * ``students(institution_id)``    — tenant binding
        * ``students.approval_status``    — Phase 6.4 approval lifecycle
        * ``students.is_active``          — Phase 6.2 lifecycle flag

    The tenant, roles, and organization/institution scope used AFTER sign-in
    continue to come from ``get_user_by_auth_id`` / ``user_roles`` (trusted
    server-side records); the client can never supply any of them.
    """
    client = get_admin_client()
    response = (
        client.table("users")
        .select(
            "user_id:id, status, "
            "students(institution_id, approval_status, is_active)"
        )
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        return None
    row = response.data
    student_links = row.get("students") or []
    # PostgREST embeds the one-to-one students relation as a single object
    # when the FK is detected as one-to-one, and as a list otherwise —
    # handle both shapes (same as get_user_by_auth_id).
    if isinstance(student_links, dict):
        student = student_links
    elif student_links:
        student = student_links[0]
    else:
        student = None
    return {
        "user_id": row["user_id"],
        "status": row.get("status"),
        "institution_id": student.get("institution_id") if student else None,
        "approval_status": student.get("approval_status") if student else None,
        "student_is_active": student.get("is_active") if student else None,
    }
