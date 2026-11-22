"""Staff and Faculty invited by an institution administrator."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.admin.members import memberships as routes
from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.member_invitations import MemberInvitationCreate
from app.services.admin import member_invitations as service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
ADMIN_A = "10000000-0000-0000-0000-000000000001"
DEPT_A = UUID("60000000-0000-0000-0000-000000000001")
INVITE = UUID("50000000-0000-0000-0000-000000000001")
MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase/migrations"
client = TestClient(app, raise_server_exceptions=False)


def body(**changes) -> MemberInvitationCreate:
    data = {"email": " Ada@Example.com ", "full_name": "  Ada   Lovelace ", "role": "faculty",
            "department_id": str(DEPT_A)}
    return MemberInvitationCreate(**{**data, **changes})


def row(**changes) -> dict:
    future = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    return {"invitation_id": str(INVITE), "institution_id": str(INST_A), "email": "ada@example.com",
            "role_name": "faculty", "status": "invited", "expires_at": future, "created_at": future,
            "email_delivery_status": "pending", "invited_department_id": str(DEPT_A),
            "invited_full_name": "Ada Lovelace", "token_hash": "must-not-leak", **changes}


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_request_accepts_only_staff_or_faculty_and_no_tenant_fields() -> None:
    parsed = body()
    assert (parsed.email, parsed.full_name) == ("ada@example.com", "Ada Lovelace")
    for bad in ({"role": "admin"}, {"role": "student"}, {"institution_id": str(INST_A)},
                {"full_name": "   "}, {"email": "not-an-email"}):
        with pytest.raises(ValidationError):
            body(**bad)


def test_create_sends_only_a_digest_and_never_returns_the_token() -> None:
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.invite_repo, "generate_invitation_token", return_value="raw-token"),
        patch.object(service.email_outbox_crypto, "protect_invitation_token", return_value="sealed"),
        patch.object(service.repo, "create", return_value=row()) as create,
    ):
        result = service.create({"user_id": ADMIN_A}, INST_A, body())
    kwargs = create.call_args.kwargs
    assert kwargs["institution_id"] == INST_A and kwargs["actor_id"] == ADMIN_A
    assert kwargs["token_hash"] == service.invite_repo.hash_invitation_token("raw-token")
    assert kwargs["protected_token"] == "sealed" and "raw-token" not in str(kwargs)
    assert (kwargs["role"], kwargs["department_id"]) == ("faculty", DEPT_A)
    dumped = result.model_dump_json()
    assert "raw-token" not in dumped and "must-not-leak" not in dumped
    assert result.invitation.full_name == "Ada Lovelace" and result.email_delivery.status == "pending"


@pytest.mark.parametrize(("code", "status", "public"), [
    ("P1201", 422, "DEPARTMENT_INVALID"),
    ("P1202", 409, "MEMBER_ALREADY_EXISTS"),
    ("P1203", 409, "INVITATION_ALREADY_PENDING"),
    ("42501", 403, "FORBIDDEN"),
])
def test_database_refusals_have_clear_public_errors(code, status, public) -> None:
    failure = Exception("refused")
    failure.code = code
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.repo, "create", side_effect=failure),
    ):
        with pytest.raises(AppError) as caught:
            service.create({"user_id": ADMIN_A}, INST_A, body())
    assert (caught.value.status_code, caught.value.code) == (status, public)


def test_list_shows_pending_and_expired_but_not_closed_invitations() -> None:
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = [row(), row(invitation_id=str(UUID(int=2)), expires_at=past),
            row(invitation_id=str(UUID(int=3)), status="accepted"),
            row(invitation_id=str(UUID(int=4)), status="cancelled")]
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.repo, "list_staff_faculty", return_value=rows) as reader,
    ):
        result = service.list_pending(INST_A)
    reader.assert_called_once_with(reader.call_args.args[0], INST_A)
    assert [item.status for item in result.invitations] == ["invited", "expired"]


def test_cancel_refuses_invitations_outside_the_institution_or_role() -> None:
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.repo, "get", return_value=None),
        patch.object(service.invitations, "cancel_invitation") as cancel,
    ):
        with pytest.raises(AppError) as caught:
            service.cancel({"user_id": ADMIN_A}, INST_A, INVITE)
    assert caught.value.status_code == 404
    cancel.assert_not_called()


def test_cancel_closes_the_invitation_and_audits_once() -> None:
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.repo, "get", return_value=row()),
        patch.object(service.invitations, "cancel_invitation",
                     return_value=MagicMock(already_applied=False)) as cancel,
        patch.object(service, "record_admin_action") as audit,
    ):
        result = service.cancel({"user_id": ADMIN_A}, INST_A, INVITE)
    cancel.assert_called_once_with({"user_id": ADMIN_A}, INST_A, INVITE)
    assert audit.call_count == 1 and result.already_applied is False


def test_routes_take_the_institution_from_the_administrator() -> None:
    user = {"user_id": ADMIN_A, "institution_id": str(INST_A)}
    with (
        patch.object(routes.common, "required_institution", return_value=INST_A) as scope,
        patch.object(routes.member_invitations, "create", return_value="created") as create,
    ):
        assert routes.create_membership_invitation(body(), user) == "created"
    scope.assert_called_once_with(user)
    create.assert_called_once_with(user, INST_A, body())


def test_every_invitation_route_has_a_permission_policy() -> None:
    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/memberships/invitations")] == ("users.read",)
    assert "users.create" in _ADMIN_ROUTE_PERMISSIONS[("POST", "/admin/memberships/invitations")]
    assert ("POST", "/admin/memberships/invitations/{invitation_id}/cancel") in _ADMIN_ROUTE_PERMISSIONS


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admins_cannot_invite(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN_A, "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role], "status": "active", "role_assignments": [],
    }
    response = client.post("/api/v1/admin/memberships/invitations", json=body().model_dump(mode="json"))
    assert response.status_code == 403


def function(sql: str, name: str) -> str:
    return sql.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]


def test_creation_migration_checks_admin_department_membership_and_duplicates() -> None:
    sql = (MIGRATIONS / "20261127000000_member_invitations.sql").read_text(encoding="utf-8")
    create = function(sql, "create_member_invitation")
    checks = ["phase81_assert_institution_admin(p_actor, p_tenant)",
              "institution_id = p_tenant AND is_active", "'P1201'", "'P1202'", "'P1203'"]
    for check in checks:
        assert check in create
    insert = create.index("INSERT INTO public.platform_admin_invitations")
    assert all(create.index(check) < insert for check in checks)
    assert "admin_invited" in create and "INSERT INTO public.admin_audit_log" in create
    assert "REFERENCES public.departments" not in sql  # never blocks deleting a department
    assert "trg_member_invitation_details_immutable" in sql
    grant = sql.split("GRANT EXECUTE ON FUNCTION public.create_member_invitation(", 1)[1].split(";", 1)[0]
    assert "TO service_role" in grant and "authenticated" not in grant


def test_acceptance_records_the_approval_only_for_administrator_invitations() -> None:
    sql = (MIGRATIONS / "20261127010000_member_invitation_acceptance.sql").read_text(encoding="utf-8")
    finalize = function(sql, "b05_finalize_invitation")
    # Older invitations still need an approved request before the grant.
    assert "IF NOT v_admin_invited THEN" in finalize
    assert "mr.status = 'approved'" in finalize
    record = finalize.index("INSERT INTO public.institution_membership_requests")
    grant = finalize.index("b05_grant_institution_role(")
    assert record < grant
    assert "'approved', 'Invited by an administrator', v_invitation.created_by" in finalize
    assert "phase81_assert_institution_admin(\n                v_invitation.created_by" in finalize
    department = finalize.index("INSERT INTO public.institution_member_departments")
    assert "institution_id = v_invitation.institution_id AND is_active" in finalize[grant:department]
    assert "service_role" in finalize.split("BEGIN", 1)[1][:200]
