"""Safe institution details for the authenticated identity bootstrap."""

from app.db.supabase import get_admin_client
from app.repositories.platform import tenancy as tenancy_repo


def get_identity_institution_code(current_user: dict) -> str | None:
    """Read the public code using only the server-resolved institution key."""
    institution_id = current_user.get("institution_id")
    if not institution_id:
        return None

    institution = tenancy_repo.get_institution_by_id(get_admin_client(), institution_id)
    code = institution.get("code") if institution else None
    if not isinstance(code, str):
        return None
    return code.strip() or None
