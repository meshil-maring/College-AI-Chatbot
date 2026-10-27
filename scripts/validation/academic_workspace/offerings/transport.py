"""Scope a non-multiplexed HTTP transport to this development data loader."""

from contextlib import contextmanager
from unittest.mock import patch

import httpx
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import settings
from app.db import supabase as database


@contextmanager
def development_transport():
    # Large parallel seeds can encounter proxy HTTP/2 stream termination.
    # Use separate HTTP/1.1 connections without changing application settings
    # or blindly retrying writes whose commit outcome might be ambiguous.
    with httpx.Client(
        http2=False, timeout=httpx.Timeout(45, connect=10),
        limits=httpx.Limits(max_connections=8, max_keepalive_connections=4, keepalive_expiry=5),
    ) as session:
        client = create_client(
            settings.supabase_url, settings.supabase_secret_key,
            options=SyncClientOptions(httpx_client=session, auto_refresh_token=False, persist_session=False),
        )
        config = (settings.supabase_url, settings.supabase_secret_key)
        with patch.object(database, "_admin_client", client), patch.object(database, "_admin_client_config", config):
            yield client
