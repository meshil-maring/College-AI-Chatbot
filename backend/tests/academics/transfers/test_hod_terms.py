"""Head of Department terms and the one-department policy."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.academics import student_transfers as service
from ..support import principal
from .test_api import client_for
from .test_migration import SOURCE, generator


def terms_sql():
    target, sql = generator().render()[5]
    assert target.name == "20261129000000_department_head_terms.sql"
    return sql


def body(sql, name):
    return sql.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]


def test_add_route_passes_the_term_and_rejects_an_inverted_one():
    user, department, faculty = {"user_id": str(uuid4())}, str(uuid4()), str(uuid4())
    base = f"/api/v1/admin/department-heads/{department}/heads"
    start, end = date(2026, 7, 1), date(2027, 6, 30)
    with client_for(user) as client, patch.object(service, "add_department_head", return_value={}) as adder:
        ok = client.post(base, json={"faculty_user_id": faculty, "starts_on": str(start), "planned_end_on": str(end)})
        inverted = client.post(base, json={"faculty_user_id": faculty, "starts_on": str(end),
                                           "planned_end_on": str(start)})
    assert (ok.status_code, inverted.status_code) == (201, 422)
    adder.assert_called_once_with(user, department, faculty, start, end)


def test_term_and_policy_routes_take_identity_from_the_path():
    user, department, faculty = {"user_id": str(uuid4())}, str(uuid4()), str(uuid4())
    with (
        client_for(user) as client,
        patch.object(service, "set_department_head_term", return_value={}) as term,
        patch.object(service, "set_department_head_policy", return_value={}) as policy,
    ):
        url = f"/api/v1/admin/department-heads/{department}/heads/{faculty}/term"
        assert client.put(url, json={"starts_on": "2026-07-01"}).status_code == 200
        assert client.put(url, json={}).status_code == 422
        assert client.put("/api/v1/admin/department-head-policy",
                          json={"allow_multi_department_hod": False}).status_code == 200
        assert client.put("/api/v1/admin/department-head-policy",
                          json={"allow_multi_department_hod": False, "institution_id": "x"}).status_code == 422
    term.assert_called_once_with(user, department, faculty, date(2026, 7, 1), None)
    policy.assert_called_once_with(user, False)


@pytest.mark.parametrize("command,args", [
    ("set_department_head_term", (str(uuid4()), str(uuid4()), date.today(), None)),
    ("set_department_head_policy", (False,)),
])
def test_term_and_policy_require_department_management(command, args):
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError) as caught:
            getattr(service, command)(principal(["departments.read"]), *args)
    assert caught.value.status_code == 403
    database.assert_not_called()


def test_dates_are_sent_as_iso_strings():
    client = MagicMock()
    start = date.today() - timedelta(days=3)
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service, "validated_scope_permissions", return_value=["departments.manage"]),
        patch.object(service.repository, "set_department_head_term", return_value={}) as writer,
    ):
        service.set_department_head_term(principal(["departments.manage"]), "d", "f", start, None)
    assert writer.call_args.args[-2:] == (start.isoformat(), None)


@pytest.mark.parametrize("sqlstate,status,code", [
    ("P1114", 409, "DEPARTMENT_HEAD_POLICY"),
    ("P1115", 422, "DEPARTMENT_HEAD_TERM_INVALID"),
    ("P1111", 409, "STUDENT_HAS_OPEN_TRANSFER"),  # unchanged meaning
])
def test_hod_errors_have_their_own_codes(sqlstate, status, code):
    failure = Exception("refused")
    failure.code = sqlstate
    with (
        patch.object(service, "get_admin_client", return_value=MagicMock()),
        patch.object(service, "validated_scope_permissions", return_value=["departments.manage"]),
        patch.object(service.repository, "add_department_head", side_effect=failure),
    ):
        with pytest.raises(AppError) as caught:
            service.add_department_head(principal(["departments.manage"]), str(uuid4()), str(uuid4()))
    assert (caught.value.status_code, caught.value.code) == (status, code)


def test_every_authority_check_honors_the_planned_end_date():
    sql = terms_sql()
    for name in ("transfer_hod_departments", "department_head_ids", "read_department_heads"):
        assert "department_head_in_effect(h.ended_at, h.planned_end_on)" in body(sql, name), name
    lock = body(sql, "department_head_lock")
    assert lock.index("transfer_admin_allowed") < lock.index("UPDATE public.department_heads")
    assert "academic.department.head.expired" in lock


def test_new_appointments_are_guarded_and_the_policy_defaults_to_allowed():
    sql = terms_sql()
    assert "ADD COLUMN allow_multi_department_hod boolean NOT NULL DEFAULT true" in sql
    guard = body(sql, "department_head_guard")
    assert "'P1114'" in guard and "'P1115'" in guard and "TG_OP = 'INSERT'" in guard
    assert "BEFORE INSERT OR UPDATE OF starts_on, planned_end_on ON public.department_heads" in sql
    assert "DROP FUNCTION public.add_department_head(uuid, uuid, uuid, uuid);" in sql
    grants = sql.split("GRANT EXECUTE ON FUNCTION", 1)[1].split(";", 1)[0]
    assert "department_head_in_effect" not in grants and "TO service_role" in grants
    for path in (SOURCE / "hod_terms").glob("*.sql"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 250, path.name
