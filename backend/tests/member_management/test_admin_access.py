"""Administrator access areas: account loading, the Owner's command and migrations.

Behaviour against a real database is covered by sql/admin_access_contracts.sql.
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.core.errors import AppError
from app.core.security.admin_access import admin_access_limits, limit_grant_permissions
from app.db import supabase
from app.schemas.admin.institution_admins import AdminAccessUpdate, AdminInvitationCreate
from app.services.admin import institution_admins as service

INST_A = "40000000-0000-0000-0000-000000000001"
INST_B = "40000000-0000-0000-0000-000000000002"
OWNER = "10000000-0000-0000-0000-000000000001"
OTHER = UUID("10000000-0000-0000-0000-000000000002")
MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase/migrations"
ADMIN_CODES = ["users.read", "users.update", "notices.read", "students.read", "brand.new"]


def grant(role, tenant):
    return {"scope_type": "institution", "scope_id": tenant, "scope_organization_id": None,
            "roles": {"name": role, "is_active": True, "role_permissions": [
                {"permissions": {"code": code, "scope": "global", "is_active": True}} for code in ADMIN_CODES]}}


class Query:
    def __init__(self, data=None, failure=None):
        self.data, self.failure, self.projection = data, failure, None

    def select(self, projection):
        self.projection = projection
        return self

    def eq(self, *_args):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        if self.failure:
            raise self.failure
        return SimpleNamespace(data=self.data)


def load(access_rows=None, failure=None, roles=("admin", "admin")):
    row = {"user_id": OWNER, "auth_user_id": "auth", "email": "a@x.test", "status": "active",
           "user_roles": [grant(roles[0], INST_A), grant(roles[1], INST_B)], "user_permission_grants": [],
           "students": []}
    tables = {"users": Query(row), "institution_admin_access": Query(access_rows or [], failure)}
    client = SimpleNamespace(table=lambda name: tables[name])
    with patch("app.db.supabase.get_admin_client", return_value=client):
        user = asyncio.run(supabase.get_user_by_auth_id("auth", include_permissions=True))
    return user, tables


def coded(code):
    failure = Exception("database said no")
    failure.code = code
    return failure


def test_a_limited_admin_grant_keeps_only_the_allowed_codes_of_that_institution():
    user, tables = load([{"institution_id": INST_A, "allowed_codes": ["notices.read", "profile.own.read"]}])
    by_tenant = {item["scope_id"]: item["permissions"] for item in user["role_assignments"]}
    assert by_tenant[INST_A] == ["notices.read"]
    assert by_tenant[INST_B] == sorted(ADMIN_CODES)  # another institution's grant is untouched
    # Sign-in never embeds the limit table in the account query.
    assert "institution_admin_access" not in tables["users"].projection


def test_no_limit_means_full_access_and_future_codes_are_kept():
    user, _ = load([])
    assert user["role_assignments"][0]["permissions"] == sorted(ADMIN_CODES)
    assert "brand.new" in user["effective_permissions"]


@pytest.mark.parametrize("code", ["PGRST205", "42P01"])
def test_sign_in_works_before_the_access_migration_is_applied(code):
    user, _ = load(failure=coded(code))
    assert user["role_assignments"][0]["permissions"] == sorted(ADMIN_CODES)


def test_other_limit_read_failures_refuse_rather_than_grant_full_access():
    with pytest.raises(Exception, match="database said no"):
        load(failure=coded("08006"))


def test_accounts_without_an_admin_grant_never_read_the_limit_table():
    user, tables = load(failure=coded("08006"), roles=("staff", "faculty"))
    assert user is not None and tables["institution_admin_access"].projection is None


def test_limits_apply_only_to_institution_admin_grants():
    limits = admin_access_limits({"institution_id": INST_A, "allowed_codes": []})
    assert limit_grant_permissions("admin", "institution", INST_A, {"users.read"}, limits) == set()
    assert limit_grant_permissions("staff", "institution", INST_A, {"users.read"}, limits) == {"users.read"}
    assert limit_grant_permissions("admin", "platform", INST_A, {"users.read"}, limits) == {"users.read"}
    assert admin_access_limits("unexpected") == {}


def test_access_body_accepts_known_areas_once_or_null_for_full_access():
    assert AdminAccessUpdate(access_areas=None).access_areas is None
    assert AdminAccessUpdate(access_areas=[]).access_areas == []
    for bad in (["everything"], ["content", "content"]):
        with pytest.raises(ValidationError):
            AdminAccessUpdate(access_areas=bad)
    with pytest.raises(ValidationError):
        AdminAccessUpdate.model_validate({})  # must say what access to give
    invite = AdminInvitationCreate(email="n@example.com", access_areas=["students"])
    assert invite.access_areas == ["students"]


def test_owner_sets_access_through_the_audited_command():
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "set_access", return_value={"full_access": False}) as command:
        result = service.set_access({"user_id": OWNER}, UUID(INST_A), OTHER,
                                    AdminAccessUpdate(access_areas=["content"]))
    command.assert_called_once_with("db", OWNER, UUID(INST_A), OTHER, ["content"])
    assert result.message.startswith("Access updated")


def test_owner_cannot_limit_themselves():
    failure = Exception("raw")
    failure.code = "P1404"
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "set_access", side_effect=failure):
        with pytest.raises(AppError) as error:
            service.set_access({"user_id": OWNER}, UUID(INST_A), UUID(OWNER), AdminAccessUpdate(access_areas=[]))
    assert (error.value.status_code, error.value.code) == (409, "OWNER_ALWAYS_FULL_ACCESS")


def test_access_route_is_owner_level_policy():
    assert _ADMIN_ROUTE_PERMISSIONS[("PUT", "/admin/institution-admins/{user_id}/access")] == ("roles.manage",)


def test_migrations_keep_helpers_internal_and_the_owner_unlimited():
    access = (MIGRATIONS / "20261202000000_institution_admin_access.sql").read_text(encoding="utf-8")
    enforce = (MIGRATIONS / "20261202010000_admin_access_enforcement.sql").read_text(encoding="utf-8")
    transfer = (MIGRATIONS / "20261202020000_transfer_admin_access.sql").read_text(encoding="utf-8")
    assert "institution_owner_assert(p_actor, p_tenant)" in access.split("set_institution_admin_access(", 1)[1]
    assert "institutions_owner_clear_access" in access
    assert "GRANT SELECT ON TABLE public.institution_admin_access TO service_role" in access
    assert "institution_owner_assert(p_actor, p_tenant)" in enforce.split("create_admin_invitation(", 2)[2]
    assert "institution_admin_access_allows(NEW.granted_by" in enforce
    assert "institution_admin_access_allows(p_actor, p_tenant, 'users.update')" in enforce
    assert "institution_admin_access_allows(p_actor, p_tenant, p_permission)" in transfer
    for sql in (access, enforce, transfer):
        assert len(sql.splitlines()) <= 250
