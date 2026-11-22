from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.academics import teaching_assignments as service
from ..support import TENANT, principal


def test_request_passes_only_the_authenticated_actor_and_tenant():
    user, client = principal(), MagicMock()
    offering, faculty = uuid4(), uuid4()
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "request", return_value={"status": "pending"}) as writer,
    ):
        result = service.request(user, {
            "academic_offering_id": offering, "faculty_user_id": faculty,
            "starts_on": date(2026, 12, 1), "planned_end_on": None,
        })
    assert result == {"status": "pending"}
    writer.assert_called_once_with(
        client, user["user_id"], TENANT, str(offering), str(faculty), "2026-12-01", None,
    )


def test_decision_maps_the_action_to_approve_or_reject():
    user, client, assignment = principal(), MagicMock(), str(uuid4())
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "decide", return_value={}) as writer,
    ):
        service.decide(user, assignment, "approve", None)
        service.decide(user, assignment, "reject", "Clash")
    assert [call.args[4:] for call in writer.call_args_list] == [(True, None), (False, "Clash")]


@pytest.mark.parametrize("user", [{"user_id": str(uuid4())}, {"institution_id": TENANT}])
def test_a_request_without_actor_or_tenant_is_refused_before_the_database(user):
    with patch.object(service, "get_admin_client") as client:
        with pytest.raises(AppError) as error:
            service.overview(user)
    assert error.value.status_code == 403
    client.assert_not_called()


@pytest.mark.parametrize(("code", "status", "public_code"), [
    ("P1501", 422, "TEACHING_OFFERING_UNAVAILABLE"),
    ("P1503", 403, "TEACHING_SCOPE"),
    ("P1504", 409, "TEACHING_ALREADY_DECIDED"),
    ("P1506", 422, "TEACHING_REASON_REQUIRED"),
    ("42501", 403, "FORBIDDEN"),
    ("P0002", 404, "TEACHING_ASSIGNMENT_NOT_FOUND"),
])
def test_database_refusals_become_clear_errors(code, status, public_code):
    failure = Exception("raw database text")
    failure.code = code
    with (
        patch.object(service, "get_admin_client", return_value=MagicMock()),
        patch.object(service.repository, "end", side_effect=failure),
    ):
        with pytest.raises(AppError) as error:
            service.end(principal(), str(uuid4()))
    assert (error.value.status_code, error.value.code) == (status, public_code)
    assert "raw database text" not in error.value.message


def test_unknown_database_failures_do_not_leak_details():
    with (
        patch.object(service, "get_admin_client", return_value=MagicMock()),
        patch.object(service.repository, "overview", side_effect=Exception("boom")),
    ):
        with pytest.raises(AppError) as error:
            service.overview(principal())
    assert error.value.status_code == 500
    assert "boom" not in error.value.message
