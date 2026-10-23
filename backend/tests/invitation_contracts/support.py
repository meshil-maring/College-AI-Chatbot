"""Mocked invitation recovery fixtures and fixed source paths."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from app.repositories.invitations import platform_admin_invitations as repo
from app.services.invitations import platform_admin_invitations as institution
from app.services.invitations import super_admin_registration as platform
from app.services.auth import student_registration as accounts

ROOT = Path(__file__).parents[3]
SQL = ROOT / "supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql"
TOKEN = "a" * 64
INV = "20000000-0000-0000-0000-000000000001"
USER = "30000000-0000-0000-0000-000000000001"
AUTH = "50000000-0000-0000-0000-000000000001"
INST = "40000000-0000-0000-0000-000000000001"
OP = "60000000-0000-0000-0000-000000000001"
ACTOR = {"user_id": USER, "auth_user_id": AUTH}


@pytest.fixture
def recovery(monkeypatch):
    client = MagicMock()
    invitation = {
        "invitation_id": INV,
        "institution_id": INST,
        "role_name": "admin",
        "email": "new@example.test",
        "status": "accepted",
        "acceptance_id": OP,
    }
    operation = {
        "acceptance_id": OP,
        "stage": "accepted",
        "user_id": USER,
        "auth_user_id": AUTH,
        "new_account": True,
    }
    for service, resolver in (
        (institution, "_resolve_live_invitation"),
        (platform, "_resolve_live"),
    ):
        monkeypatch.setattr(service, "get_admin_client", lambda: client)
        monkeypatch.setattr(service, resolver, lambda *_: invitation.copy())
        monkeypatch.setattr(service.abuse, "enforce_accept_rate_limit", lambda *_: None)
        monkeypatch.setattr(
            service.abuse, "enforce_inspect_rate_limit", lambda *_: None
        )
    monkeypatch.setattr(
        institution,
        "_require_institution",
        lambda *_: {"name": "Example", "code": "EX"},
    )
    read = MagicMock(side_effect=lambda *a, **k: operation.copy())
    monkeypatch.setattr(repo, "recover_accepted_operation", read)

    def advance(*a, **k):
        if operation["stage"] != k["expected_stage"]:
            return None
        operation["stage"] = k["stage"]
        return operation.copy()

    monkeypatch.setattr(repo, "advance_operation", MagicMock(side_effect=advance))
    create = MagicMock()
    monkeypatch.setattr(accounts, "_create_auth_account", create)
    reserve, grant = MagicMock(), MagicMock()
    monkeypatch.setattr(repo, "reserve_invitation", reserve)
    monkeypatch.setattr(repo, "claim_invitation", grant)
    return client, invitation, operation, read, create, reserve, grant
