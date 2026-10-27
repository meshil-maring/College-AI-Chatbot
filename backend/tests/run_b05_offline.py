"""Run selected B05 tests with dotenv disabled, dummy config and no sockets.

From the repository root: .venv/Scripts/python.exe backend/tests/run_b05_offline.py
Additional arguments replace the default test selection. No SQL is executed.
"""

import socket
import sys
from pathlib import Path
from threading import local
from unittest.mock import patch

from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.dont_write_bytecode = True

DEFAULT_TESTS = [
    "test_b05_stage14_source_fixes.py",
    "test_b05_invitation_acceptance_security.py",
    "test_phase_7_14_super_admin_university_admin_lifecycle.py",
    "test_phase_7_15_invitation_delivery_email_verification.py",
    "test_phase_7_23_staff_faculty_onboarding_roster.py",
    "test_phase_9_super_admin_registration.py",
    "test_phase_7_13_super_admin_institution_management.py",
    "test_phase_7_12_super_admin_authorization.py",
    "test_phase_8_1_authorization.py",
    "test_role_scope_enforcement_phase_6_13_7.py",
    "platform_tenancy",
    "test_student_approval_phase_6_4.py",
    "test_phase_7_17_email_outbox_worker.py",
]
OFFLINE_SETTINGS = {
    "environment": "test", "debug": True,
    "supabase_url": "http://127.0.0.1:9",
    "supabase_publishable_key": "sb_publishable_offline_dummy",
    "supabase_secret_key": "sb_secret_offline_dummy",
}


_socketpair_context = local()
_original_connect = socket.socket.connect
_original_socketpair = socket.socketpair


def isolated_socketpair(*args, **kwargs):
    # Windows implements socketpair using a temporary loopback connection.
    # Allow only the stdlib call that constructs asyncio's internal wakeup pair.
    _socketpair_context.active = True
    try:
        return _original_socketpair(*args, **kwargs)
    finally:
        _socketpair_context.active = False


def guarded_connect(*args, **kwargs):
    if getattr(_socketpair_context, "active", False):
        return _original_connect(*args, **kwargs)
    return deny_network(*args, **kwargs)


def deny_network(*args, **kwargs):
    raise AssertionError("B05 offline tests prohibit network connections")


if __name__ == "__main__":
    with (
        patch.object(DotEnvSettingsSource, "_read_env_files", return_value={}),
        patch.object(EnvSettingsSource, "__call__", return_value=OFFLINE_SETTINGS),
        patch.object(socket, "socketpair", isolated_socketpair),
        patch.object(socket.socket, "connect", guarded_connect),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        import pytest

        arguments = sys.argv[1:]
        explicit_paths = any(".py" in arg and not arg.startswith("-") for arg in arguments)
        selection = arguments if explicit_paths else [
            *[str(ROOT / "backend/tests" / name) for name in DEFAULT_TESTS], *arguments,
        ]
        raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", *selection]))
