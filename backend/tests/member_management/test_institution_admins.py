"""Institution administrators and the Owner: service, routes and migrations."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.api.admin.members import administrators as routes
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.institution_admins import AdminInvitationCreate
from app.services.admin import institution_admins as service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
OWNER = "10000000-0000-0000-0000-000000000001"
OTHER = "10000000-0000-0000-0000-000000000002"
MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase/migrations"
NAMES = ["20261130000000_institution_owner.sql", "20261130010000_owner_admin_invitations.sql",
         "20261130020000_owner_admin_acceptance.sql"]
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def listing(owner=OWNER):
    return {"owner_user_id": owner, "invitations": [],
            "administrators": [{"user_id": OWNER, "name": "Olive", "email": "o@x.test", "status": "active"},
                               {"user_id": OTHER, "name": "Abe", "email": "a@x.test", "status": "active"}]}


@pytest.mark.parametrize("viewer,is_owner", [(OWNER, True), (OTHER, False)])
def test_listing_marks_the_owner_and_whether_the_viewer_is_owner(viewer, is_owner) -> None:
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "read", return_value=listing()):
        result = service.list_admins({"user_id": viewer}, INST_A)
    assert result.viewer_is_owner is is_owner
    assert [admin.is_owner for admin in result.administrators] == [True, False]


def test_listing_without_an_owner_marks_nobody() -> None:
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "read", return_value=listing(owner=None)):
        result = service.list_admins({"user_id": OWNER}, INST_A)
    assert not result.viewer_is_owner and not any(admin.is_owner for admin in result.administrators)


def test_invitation_sends_only_a_digest_and_never_returns_the_token() -> None:
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.invite_repo, "generate_invitation_token", return_value="raw-token"), \
            patch.object(service.email_outbox_crypto, "protect_invitation_token", return_value="sealed"), \
            patch.object(service.repo, "create_invitation", return_value={}) as create:
        result = service.invite({"user_id": OWNER}, INST_A, AdminInvitationCreate(email=" New@Example.com ", full_name=" "))
    kwargs = create.call_args.kwargs
    assert kwargs["email"] == "new@example.com" and kwargs["full_name"] is None
    assert kwargs["token_hash"] != "raw-token" and kwargs["protected_token"] == "sealed"
    assert "raw-token" not in result.model_dump_json()


def test_invitation_contract_rejects_tenant_or_role_fields() -> None:
    for extra in ({"role": "admin"}, {"institution_id": str(INST_A)}, {"email": "nope"}):
        with pytest.raises(ValidationError):
            AdminInvitationCreate(**{"email": "a@example.com", **extra})


@pytest.mark.parametrize("sqlstate,status,code", [
    ("P1401", 403, "OWNER_REQUIRED"), ("P1402", 422, "NOT_AN_ADMINISTRATOR"),
    ("P1403", 409, "OWNER_CANNOT_BE_REMOVED"), ("42501", 403, "FORBIDDEN"),
    ("XX000", 502, "ADMINISTRATOR_COMMAND_FAILED"),
])
def test_database_refusals_become_safe_api_errors(sqlstate, status, code) -> None:
    failure = Exception("database")
    failure.code = sqlstate
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "revoke", side_effect=failure):
        with pytest.raises(AppError) as caught:
            service.revoke({"user_id": OWNER}, INST_A, UUID(OTHER))
    assert (caught.value.status_code, caught.value.code) == (status, code)


def test_every_route_has_a_policy_and_uses_the_administrators_institution() -> None:
    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/institution-admins")] == ("users.read",)
    for key in [("POST", "/admin/institution-admins/invitations"),
                ("POST", "/admin/institution-admins/invitations/{invitation_id}/cancel"),
                ("DELETE", "/admin/institution-admins/{user_id}"), ("PUT", "/admin/institution-admins/owner")]:
        assert "roles.manage" in _ADMIN_ROUTE_PERMISSIONS[key]
    actor = {"user_id": OWNER}
    with patch.object(routes.common, "required_institution", return_value=INST_A) as scope, \
            patch.object(routes.institution_admins, "revoke", return_value="ok") as revoke:
        assert routes.revoke_administrator(UUID(OTHER), actor) == "ok"
    scope.assert_called_once_with(actor)
    revoke.assert_called_once_with(actor, INST_A, UUID(OTHER))


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admins_cannot_reach_administrator_routes(role) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": OWNER, "auth_user_id": "70000000-0000-0000-0000-000000000009",
        "roles": [role], "status": "active", "role_assignments": [],
    }
    assert client.get("/api/v1/admin/institution-admins").status_code == 403
    assert client.put("/api/v1/admin/institution-admins/owner", json={"user_id": OTHER}).status_code == 403


def test_an_administrator_passes_the_permission_boundary() -> None:
    """Regression: the policy lookup keeps everything from the last "/admin" in the
    path, so a route first named "/admin/administrators" was refused for everyone."""
    granted = ["users.read", "users.create", "roles.manage"]
    actor = {
        "user_id": OWNER, "institution_id": str(INST_A), "roles": ["admin"], "status": "active",
        "permissions_resolved": True, "scoped_permissions_resolved": True, "effective_permissions": granted,
        "role_assignments": [{"role": "admin", "scope_type": "institution", "scope_id": str(INST_A),
                              "scope_organization_id": "50000000-0000-0000-0000-000000000001",
                              "is_active": True, "permissions": granted}],
    }
    app.dependency_overrides[get_current_user] = lambda: actor
    # The boundary re-checks that the administrator's institution is active.
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
        SimpleNamespace(data={"status": "active", "is_active": True}))
    with patch("app.services.auth.authorization.get_admin_client", return_value=db),             patch.object(service, "list_admins", return_value={"owner_user_id": None, "viewer_is_owner": False,
                                                               "administrators": [], "invitations": []}) as listed:
        response = client.get("/api/v1/admin/institution-admins")
    assert response.status_code == 200
    listed.assert_called_once()


def function(sql: str, name: str) -> str:
    return sql.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]


def test_owner_commands_assert_the_owner_and_stay_service_role_only() -> None:
    owner, invites, accept = (MIGRATIONS / name for name in NAMES)
    owner_sql, invite_sql = owner.read_text(encoding="utf-8"), invites.read_text(encoding="utf-8")
    for name in ("transfer_institution_ownership", "revoke_institution_admin"):
        assert "institution_owner_assert(p_actor, p_tenant)" in function(owner_sql, name), name
    for name in ("create_admin_invitation", "cancel_admin_invitation"):
        assert "institution_owner_assert(p_actor, p_tenant)" in function(invite_sql, name), name
    assert "phase81_assert_institution_admin(p_actor, p_tenant)" in function(owner_sql, "read_institution_admins")
    assert "FROM PUBLIC, anon, authenticated, service_role" in owner_sql  # helpers stay internal
    for path in (owner, invites, accept):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 250, path.name


def test_acceptance_checks_the_owner_only_for_owner_invitations() -> None:
    for name, function_name in [(NAMES[1], "b05_reserve_invitation"), (NAMES[2], "b05_finalize_invitation")]:
        body = function((MIGRATIONS / name).read_text(encoding="utf-8"), function_name)
        owner_check = body.index("institution_owner_assert(v_invitation.created_by")
        # Nested under the admin branch; non-owner invitations keep the platform check.
        assert body.rindex("IF v_invitation.admin_invited THEN", 0, owner_check) < owner_check
        assert "b05_assert_platform_actor(v_invitation.created_by)" in body[owner_check:]
