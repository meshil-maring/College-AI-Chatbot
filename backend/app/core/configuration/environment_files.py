"""Choose which dotenv files configure the backend.

By default only `.env` is read, which points at the hosted (live) project.
Setting `BACKEND_ENV=local` also reads `.env.local`, whose values win, so tests
and migration rehearsals can run against the local Supabase stack without
editing `.env`. A local run must never reach a remote database.
"""

import os
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


def backend_mode() -> str:
    mode = os.environ.get("BACKEND_ENV", "").strip().lower()
    if mode not in {"", "local"}:
        raise ValueError("BACKEND_ENV must be empty or 'local'")
    return mode


def backend_env_files() -> str | tuple[str, ...]:
    return (".env", ".env.local") if backend_mode() == "local" else ".env"


def assert_local_target(supabase_url: str) -> None:
    """Fail closed when BACKEND_ENV=local still points at a remote project."""
    if backend_mode() != "local":
        return
    host = (urlparse(supabase_url or "").hostname or "").lower()
    if host not in LOCAL_HOSTS:
        raise RuntimeError(
            "BACKEND_ENV=local requires SUPABASE_URL to point at the local stack; "
            "run scripts/local_stack/write_local_env.py after `supabase start`."
        )
