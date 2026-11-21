"""Several Heads of Department per department, and several departments per head."""

import re
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.academics import student_transfers as service
from ..support import TENANT, principal
from .test_api import client_for
from .test_migration import SOURCE, generator


def co_head_sql():
    target, sql = generator().render()[4]
    assert target.name == "20261126000000_department_co_heads.sql"
    return sql


def body(sql, name):
    return sql.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]


def test_add_and_end_routes_take_identity_only_from_the_path_and_body():
    user, department, faculty = {"user_id": str(uuid4())}, str(uuid4()), str(uuid4())
    base = f"/api/v1/admin/department-heads/{department}/heads"
    with (
        client_for(user) as client,
        patch.object(service, "add_department_head", return_value={}) as adder,
        patch.object(service, "end_department_head", return_value={}) as ender,
    ):
        assert client.post(base, json={"faculty_user_id": faculty}).status_code == 201
        assert client.post(base, json={}).status_code == 422
        assert client.post(base, json={"faculty_user_id": None}).status_code == 422
        assert client.post(base, json={"faculty_user_id": faculty, "institution_id": TENANT}).status_code == 422
        assert client.delete(f"{base}/{faculty}").status_code == 200
        assert client.delete(f"{base}/not-a-uuid").status_code == 422
    adder.assert_called_once_with(user, department, faculty)
    ender.assert_called_once_with(user, department, faculty)


@pytest.mark.parametrize("command", ["add_department_head", "end_department_head"])
@pytest.mark.parametrize("permissions", [[], ["departments.read"]])
def test_single_appointment_commands_require_department_management(command, permissions):
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError) as caught:
            getattr(service, command)(principal(permissions), str(uuid4()), str(uuid4()))
    assert caught.value.status_code == 403
    database.assert_not_called()


@pytest.mark.parametrize("command", ["add_department_head", "end_department_head"])
def test_single_appointment_commands_revalidate_scope_and_call_the_writer(command):
    user, client = principal(["departments.manage"]), MagicMock()
    department, faculty = str(uuid4()), str(uuid4())
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service, "validated_scope_permissions", return_value=["departments.manage"]) as scope,
        patch.object(service.repository, command, return_value={"already_applied": False}) as writer,
    ):
        assert getattr(service, command)(user, department, faculty) == {"already_applied": False}
    scope.assert_called_once_with(client, user, TENANT)
    writer.assert_called_once_with(client, user["user_id"], TENANT, department, faculty)


def test_invalid_appointment_reports_the_existing_public_error():
    failure = Exception("refused")
    failure.code = "P1110"
    with (
        patch.object(service, "get_admin_client", return_value=MagicMock()),
        patch.object(service, "validated_scope_permissions", return_value=["departments.manage"]),
        patch.object(service.repository, "add_department_head", side_effect=failure),
    ):
        with pytest.raises(AppError) as caught:
            service.add_department_head(principal(["departments.manage"]), str(uuid4()), str(uuid4()))
    assert (caught.value.status_code, caught.value.code) == (422, "DEPARTMENT_HEAD_INVALID")


def test_migration_allows_co_heads_but_never_duplicate_appointments():
    sql = co_head_sql()
    assert "DROP INDEX public.department_heads_one_current;" in sql
    assert "ON public.department_heads (department_id, faculty_user_id) WHERE ended_at IS NULL" in sql
    # Ended appointments are kept: nothing deletes appointment history.
    assert "DELETE FROM public.department_heads" not in sql


def test_every_appointment_command_is_guarded_locked_and_audited():
    sql = co_head_sql()
    lock = body(sql, "department_head_lock")
    for guard in ("assert_transfer_backend()", "'departments.manage'", "institution_id = p_tenant", "FOR UPDATE"):
        assert guard in lock
    for name in ("add_department_head", "end_department_head", "assign_department_head"):
        command = body(sql, name)
        assert "public.department_head_lock(p_actor, p_tenant, p_department)" in command, name
        assert "INSERT INTO public.admin_audit_log" in command, name
    add = body(sql, "add_department_head")
    assert "transfer_is_active_faculty(p_faculty, p_tenant)" in add and "'P1110'" in add
    assert add.index("'P1110'") < add.index("INSERT INTO public.department_heads")
    # Ending one appointment never touches the department's other heads.
    assert "AND faculty_user_id = p_faculty AND ended_at IS NULL" in body(sql, "end_department_head")
    assert "assert_transfer_backend()" in body(sql, "read_department_heads")


def test_only_commands_reach_the_service_role():
    sql = co_head_sql()
    security = (SOURCE / "co_heads/security.sql").read_text(encoding="utf-8")
    revoke, grant = security.split("GRANT EXECUTE", 1)
    created = {name for _, name in re.findall(r"CREATE (OR REPLACE )?FUNCTION public\.(\w+)", sql)}
    assert created <= set(re.findall(r"public\.(\w+)\(", revoke))
    assert set(re.findall(r"public\.(\w+)\(", grant)) == {
        "read_department_heads", "add_department_head", "end_department_head", "assign_department_head",
    }
    assert "authenticated" not in grant and "anon" not in grant
