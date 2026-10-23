"""Institution-scoped staff permission delegation."""

from collections.abc import Iterable
from uuid import UUID

from app.core.errors import AppError
from app.core.permissions import DELEGABLE_STAFF_PERMISSIONS
from app.db.supabase import get_admin_client
from app.repositories.shared.query_pages import read_one, read_rows


def _staff_member(user_id: UUID, institution_id: UUID) -> dict:
    result = read_one(
        get_admin_client()
        .table("users")
        .select(
            "id, status, email, first_name, last_name, "
            "user_roles!inner(scope_type, scope_id, roles!inner(name, is_active))"
        )
        .eq("id", str(user_id))
        .eq("status", "active")
        .eq("user_roles.scope_type", "institution")
        .eq("user_roles.scope_id", str(institution_id))
        .eq("user_roles.roles.name", "staff")
        .eq("user_roles.roles.is_active", True)
        .maybe_single()
    )
    if result is None:
        raise AppError("Active Staff member not found", 404, "STAFF_MEMBER_NOT_FOUND")
    return result


def list_delegable_permissions() -> list[str]:
    client = get_admin_client()
    rows = read_rows(
        client.table("permissions")
        .select("code")
        .in_("code", sorted(DELEGABLE_STAFF_PERMISSIONS))
        .eq("is_active", True)
        .order("code")
    )
    active_codes = {row["code"] for row in rows}
    return sorted(active_codes & DELEGABLE_STAFF_PERMISSIONS)


def list_staff_permissions(user_id: UUID, institution_id: UUID) -> dict:
    _staff_member(user_id, institution_id)
    client = get_admin_client()
    grants = read_rows(
        client.table("user_roles")
        .select(
            "scope_type, scope_id, roles(name, is_active, "
            "role_permissions(permissions(code, is_active)))"
        )
        .eq("user_id", str(user_id))
        .eq("scope_type", "institution")
        .eq("scope_id", str(institution_id))
    )
    inherited: set[str] = set()
    for grant in grants:
        role = grant.get("roles")
        if not isinstance(role, dict) or not role.get("is_active", True):
            continue
        for role_permission in role.get("role_permissions") or []:
            permission = role_permission.get("permissions")
            if isinstance(permission, dict) and permission.get("is_active", True):
                code = permission.get("code")
                if isinstance(code, str):
                    inherited.add(code)

    direct_rows = read_rows(
        client.table("user_permission_grants")
        .select("grant_id, granted_at, permissions(code, is_active)")
        .eq("user_id", str(user_id))
        .eq("institution_id", str(institution_id))
        .is_("revoked_at", "null")
        .order("granted_at")
    )
    direct = {
        permission["code"]: str(row["grant_id"])
        for row in direct_rows
        if isinstance((permission := row.get("permissions")), dict)
        and permission.get("is_active", True)
        and isinstance(permission.get("code"), str)
    }
    return {
        "user_id": str(user_id),
        "institution_id": str(institution_id),
        "permissions": [
            {
                "code": code,
                "inherited": code in inherited,
                "direct_grant_id": direct.get(code),
            }
            for code in sorted(inherited | set(direct))
        ],
        "delegable_permissions": list_delegable_permissions(),
    }


def change_staff_permissions(
    actor: dict,
    institution_id: UUID,
    target_user_id: UUID,
    permission_codes: Iterable[str],
    *,
    grant: bool,
) -> dict:
    codes = list(permission_codes)
    if len(codes) != len(set(codes)):
        raise AppError(
            "Duplicate permission codes are not allowed", 422, "DUPLICATE_PERMISSION"
        )
    unknown = set(codes) - DELEGABLE_STAFF_PERMISSIONS
    if unknown:
        raise AppError(
            "One or more permissions are not delegable to Staff",
            422,
            "PERMISSION_NOT_DELEGABLE",
        )
    _staff_member(target_user_id, institution_id)
    response = (
        get_admin_client()
        .rpc(
            "phase81_manage_staff_permission_grants",
            {
                "p_actor_user_id": str(actor["user_id"]),
                "p_institution_id": str(institution_id),
                "p_target_user_id": str(target_user_id),
                "p_permission_codes": codes,
                "p_grant": grant,
            },
        )
        .execute()
    )
    changed = response.data
    if not isinstance(changed, int):
        raise AppError(
            "Invalid permission mutation result", 500, "DATABASE_PROJECTION_INVALID"
        )
    return {
        "changed": changed,
        "permissions": list_staff_permissions(target_user_id, institution_id),
    }
