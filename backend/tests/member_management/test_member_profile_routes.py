"""Profile routes, permission policies and the migrations that back them."""

from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.api.admin.members import profiles as routes
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.member_invitations import MemberInvitationCreate
from app.schemas.admin.member_profiles import MemberProfileWrite
from app.services.admin import member_invitations

INST_A = UUID("40000000-0000-0000-0000-000000000001")
USER = UUID("30000000-0000-0000-0000-000000000001")
DEPT = "60000000-0000-0000-0000-000000000001"
ADMIN = {"user_id": "10000000-0000-0000-0000-000000000001", "institution_id": str(INST_A)}
PROFILE = {"common": {"employee_id": "EMP-1", "designation": "Professor", "joining_date": "2026-01-05"},
           "faculty": {"employment_type": "permanent", "employment_start_date": "2026-01-05"}}
ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "supabase/migrations"
SQL_TESTS = Path(__file__).parent / "sql"
NEW_MIGRATIONS = ["20261127020000_member_invitation_reservation.sql", "20261128000000_member_profiles.sql",
                  "20261128010000_member_profile_commands.sql", "20261128020000_member_invitation_profiles.sql"]
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_every_new_route_has_a_permission_policy() -> None:
    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/memberships/{user_id}/profile")] == ("users.read",)
    for method, path in [("PUT", "/admin/memberships/{user_id}/profile"),
                         ("PUT", "/admin/memberships/{user_id}/departments/additional"),
                         ("POST", "/admin/memberships/{user_id}/suspend")]:
        assert _ADMIN_ROUTE_PERMISSIONS[(method, path)] == ("users.update",)


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
@pytest.mark.parametrize("method,path,payload", [
    ("get", "/profile", None), ("put", "/profile", PROFILE),
    ("put", "/departments/additional", {"department_ids": []}), ("post", "/suspend", None),
])
def test_non_admins_cannot_read_or_change_profiles(role, method, path, payload) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN["user_id"], "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role], "status": "active", "role_assignments": [],
    }
    url = f"/api/v1/admin/memberships/{USER}{path}"
    response = getattr(client, method)(url, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 403


def test_routes_take_the_institution_from_the_administrator() -> None:
    body = MemberProfileWrite(**PROFILE)
    with (
        patch.object(routes.common, "required_institution", return_value=INST_A) as scope,
        patch.object(routes.member_profiles, "save_profile", return_value="saved") as save,
    ):
        assert routes.save_member_profile(USER, body, ADMIN) == "saved"
    scope.assert_called_once_with(ADMIN)
    save.assert_called_once_with(ADMIN, INST_A, USER, body)


def test_invitation_passes_the_profile_to_the_database() -> None:
    body = MemberInvitationCreate(email="ada@example.com", full_name="Ada", role="faculty",
                                  department_id=DEPT, profile=PROFILE)
    with (
        patch.object(member_invitations, "get_admin_client", return_value=object()),
        patch.object(member_invitations.email_outbox_crypto, "protect_invitation_token", return_value="p"),
        patch.object(member_invitations.repo, "create", return_value={
            "invitation_id": str(USER), "email": "ada@example.com", "role_name": "faculty",
            "invited_profile": body.database_profile()}) as create,
    ):
        result = member_invitations.create(ADMIN, INST_A, body)
    assert create.call_args.kwargs["profile"]["common"]["employee_id"] == "EMP-1"
    assert result.invitation.employee_id == "EMP-1" and result.invitation.designation == "Professor"


def test_new_migrations_stay_within_the_file_limit() -> None:
    for name in NEW_MIGRATIONS:
        assert len((MIGRATIONS / name).read_text(encoding="utf-8").splitlines()) <= 250, name


def test_reservation_only_waives_approval_for_administrator_invitations() -> None:
    sql = (MIGRATIONS / NEW_MIGRATIONS[0]).read_text(encoding="utf-8")
    block = sql.split("v_invitation.role_name IN ('staff', 'faculty') THEN", 1)[1]
    # Nested inside the institution branch, before the approved-request lookup.
    assert block.index("IF NOT v_invitation.admin_invited THEN") < block.index("mr.status = 'approved'")
    assert "TO service_role" in sql and "TO authenticated" not in sql


def test_profile_tables_are_written_only_through_audited_commands() -> None:
    tables = (MIGRATIONS / NEW_MIGRATIONS[1]).read_text(encoding="utf-8")
    assert "FROM PUBLIC, anon, authenticated, service_role" in tables
    assert "GRANT SELECT ON TABLE public.%I TO service_role" in tables
    assert "'suspended'" in tables
    commands = (MIGRATIONS / NEW_MIGRATIONS[2]).read_text(encoding="utf-8")
    for name in ("save_member_profile", "set_member_additional_departments"):
        body = commands.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]
        assert "phase81_assert_institution_admin(p_actor, p_tenant)" in body
        assert "INSERT INTO public.admin_audit_log" in body
    invitations = (MIGRATIONS / NEW_MIGRATIONS[3]).read_text(encoding="utf-8")
    assert "DROP FUNCTION public.create_member_invitation(" in invitations
    assert "AFTER UPDATE OF status ON public.platform_admin_invitations" in invitations


def test_database_contracts_cover_security_and_acceptance() -> None:
    profiles = (SQL_TESTS / "profile_contracts.sql").read_text(encoding="utf-8")
    invitations = (SQL_TESTS / "invitation_contracts.sql").read_text(encoding="utf-8")
    for probe in ("'P1204'", "'P1205'", "'42501'", "'P1201'", "has_table_privilege",
                  "has_function_privilege", "other institution admin", "suspended"):
        assert probe in profiles, probe
    for probe in ("b05_reserve_invitation", "b05_advance_invitation_operation", "b05_finalize_invitation",
                  "already_applied", "Self-service invitation", "invited profile is immutable"):
        assert probe in invitations, probe
    for path in SQL_TESTS.glob("*.sql"):
        text = path.read_text(encoding="utf-8")
        assert len(text.splitlines()) <= 250, path.name
        if path.name != "profile_fixture.sql":
            assert text.rstrip().endswith("ROLLBACK;"), path.name
