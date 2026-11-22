"""Apply the Owner's per-administrator access limit to loaded admin grants.

The Owner may limit another administrator to some access areas; the database
stores the allowed permission codes (institution_admin_access). When an account
is loaded, the codes of that institution's admin grant are intersected with
them, so every permission check, navigation item and route follows the limit.
No row means full access. Codes outside the stored list are withheld, so a
permission added to the admin role later does not reach a limited administrator.
"""

from typing import Any

# Embedded in the users projection; the hint picks the user_id foreign key
# (updated_by also references users).
ACCESS_RELATION = "institution_admin_access!institution_admin_access_user_id_fkey(institution_id, allowed_codes)"


def admin_access_limits(row: dict[str, Any]) -> dict[str, frozenset[str]]:
    """Allowed codes per institution for this account's limited admin grants."""
    rows = row.get("institution_admin_access")
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


def limit_grant_permissions(
    role: str, scope_type: str | None, scope_id: Any, permissions: set[str],
    limits: dict[str, frozenset[str]],
) -> set[str]:
    """The grant's codes, cut down to the limit of a limited institution admin grant."""
    if role != "admin" or scope_type != "institution":
        return permissions
    allowed = limits.get(str(scope_id))
    return permissions if allowed is None else permissions & allowed
