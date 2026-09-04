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
    """Return the public.users row whose auth_user_id matches, or None."""
    client = create_supabase_client()
    response = (
        client.table("users")
        .select("id, auth_user_id, email")
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    return response.data
