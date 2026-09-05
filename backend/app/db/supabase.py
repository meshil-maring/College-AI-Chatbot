from supabase import Client, create_client

from app.config import settings


def create_supabase_client() -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


def get_admin_client() -> Client:
    """Service-role client — bypasses RLS. Use only for server-side operations."""
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )


async def get_user_by_auth_id(auth_user_id: str) -> dict | None:
    """Return the public.users row whose auth_user_id matches, including active role names."""
    client = get_admin_client()
    response = (
        client.table("users")
        .select("user_id, auth_user_id, email, user_roles(roles(name, is_active))")
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    if response.data is None:
        return None
    row = response.data
    roles = [
        ur["roles"]["name"]
        for ur in (row.get("user_roles") or [])
        if ur.get("roles") and ur["roles"].get("is_active", True)
    ]
    return {"user_id": row["user_id"], "auth_user_id": row["auth_user_id"], "email": row["email"], "roles": roles}
