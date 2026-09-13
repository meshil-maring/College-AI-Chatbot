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


async def get_user_by_auth_id(auth_user_id: str) -> dict | None:
    """Return the public.users row whose auth_user_id matches, including active role names.

    The row's tenant is resolved from the one-to-one public.students profile
    (students.institution_id) when the account has one — this is the value the
    rest of the application uses for tenant isolation. Platform-level accounts
    without a student profile (e.g. admins) resolve to institution_id=None and
    are treated as unrestricted.
    """
    client = get_admin_client()
    response = (
        client.table("users")
        .select(
            "user_id, auth_user_id, email, "
            "user_roles(roles(name, is_active)), "
            "students(institution_id)"
        )
        .eq("auth_user_id", auth_user_id)
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        return None
    row = response.data
    roles = [
        ur["roles"]["name"]
        for ur in (row.get("user_roles") or [])
        if ur.get("roles") and ur["roles"].get("is_active", True)
    ]
    student_links = row.get("students") or []
    institution_id = (
        student_links[0].get("institution_id") if student_links else None
    )
    return {
        "user_id": row["user_id"],
        "auth_user_id": row["auth_user_id"],
        "email": row["email"],
        "roles": roles,
        "institution_id": institution_id,
    }
