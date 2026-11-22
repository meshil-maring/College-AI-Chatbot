"""Apply the Owner's per-administrator access limit to loaded admin grants.

The Owner may limit another administrator to some access areas; the database
stores the allowed permission codes (institution_admin_access). When an account
is loaded, the codes of that institution's admin grant are intersected with
them, so every permission check, navigation item and route follows the limit.
No row means full access. Codes outside the stored list are withheld, so a
permission added to the admin role later does not reach a limited administrator.

The limit is read separately, and only for accounts with an institution admin
grant, so sign-in never depends on it for anyone else. Before migration
20261202000000 is applied the table does not exist and no limit can exist, so
that case means full access; any other read failure refuses the request.
"""

from typing import Any

# The table is absent until 20261202000000 is applied.
_MISSING_TABLE_CODES = {"42P01", "PGRST205"}


def has_institution_admin_grant(user_roles: Any) -> bool:
    return any(
        isinstance(grant, dict) and grant.get("scope_type") == "institution"
        and isinstance(grant.get("roles"), dict) and grant["roles"].get("name") == "admin"
        for grant in user_roles or ()
    )


def admin_access_limits(rows: Any) -> dict[str, frozenset[str]]:
    """Allowed codes per institution from institution_admin_access rows."""
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return {}
    return {
        str(item["institution_id"]): frozenset(
            code for code in item.get("allowed_codes") or () if isinstance(code, str)
        )
        for item in rows
        if isinstance(item, dict) and item.get("institution_id")
    }


def fetch_admin_access_limits(client: Any, user_id: str) -> dict[str, frozenset[str]]:
    """This administrator's limits per institution; empty when none exist."""
    try:
        rows = (
            client.table("institution_admin_access")
            .select("institution_id, allowed_codes")
            .eq("user_id", user_id)
            .execute()
            .data
        )
    except Exception as exc:
        if str(getattr(exc, "code", "")) in _MISSING_TABLE_CODES:
            return {}
        raise
    return admin_access_limits(rows if isinstance(rows, list) else [])


def limit_grant_permissions(
    role: str, scope_type: str | None, scope_id: Any, permissions: set[str],
    limits: dict[str, frozenset[str]],
) -> set[str]:
    """The grant's codes, cut down to the limit of a limited institution admin grant."""
    if role != "admin" or scope_type != "institution":
        return permissions
    allowed = limits.get(str(scope_id))
    return permissions if allowed is None else permissions & allowed


def loaded_admin_limits(client: Any, row: dict[str, Any]) -> dict[str, frozenset[str]]:
    """Limits for a loaded account row; read only when it has an institution admin grant."""
    if not has_institution_admin_grant(row.get("user_roles")):
        return {}
    return fetch_admin_access_limits(client, str(row["user_id"]))


def limited_grant_permissions(
    role: str, grant: dict[str, Any], permissions: set[str], limits: dict[str, frozenset[str]],
) -> set[str]:
    return limit_grant_permissions(role, grant.get("scope_type"), grant.get("scope_id"), permissions, limits)
