from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.academics import student_transfers as service
from ..support import TENANT, principal


def student_user(permissions):
    user = principal(permissions)
    user["roles"] = ["student"]
    user["role_assignments"][0]["role"] = "student"
    return user


def student_context(user):
    return (
        patch.object(service.student_context, "get_student_context",
                     return_value={"student_id": str(uuid4()), "institution_id": TENANT}),
        patch.object(service.student_context, "assert_student_context_tenant"),
    )


def test_submission_uses_authenticated_actor_and_tenant_only():
    user = student_user(["transfers.request"])
    client, section = MagicMock(), str(uuid4())
    context, guard = student_context(user)
    with (
        context, guard,
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "submit", return_value={"status": "submitted"}) as writer,
    ):
        service.submit(user, {"to_section_id": section, "reason": "Timetable clash with work"})
    writer.assert_called_once_with(client, user["user_id"], TENANT, section, "Timetable clash with work")


@pytest.mark.parametrize("permissions", [[], ["transfers.read"], ["registration.own.manage"]])
def test_student_without_request_permission_cannot_submit_or_cancel(permissions):
    user = student_user(permissions)
    context, guard = student_context(user)
    with context, guard, patch.object(service, "get_admin_client") as database:
        for action in (
            lambda: service.submit(user, {"to_section_id": str(uuid4()), "reason": "x" * 12}),
            lambda: service.cancel(user, str(uuid4())),
        ):
            with pytest.raises(AppError) as caught:
                action()
            assert caught.value.status_code == 403
    database.assert_not_called()


def test_admin_role_grant_is_not_a_student_transfer_grant():
    user = principal(["transfers.request", "transfers.read"])  # admin-scoped grant
    context, guard = student_context(user)
    with context, guard, patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError):
            service.own_transfers(user)
    database.assert_not_called()


def test_reviewer_scope_is_decided_by_database_with_pinned_tenant():
    user = principal([])
    user["roles"] = ["faculty"]
    client = MagicMock()
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "reviews", return_value={"can_review": False}) as reader,
    ):
        assert service.reviews(user, True) == {"can_review": False}
    reader.assert_called_once_with(client, user["user_id"], TENANT, True)


def test_rejection_requires_a_reason_before_database():
    user = principal([])
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError) as caught:
            service.decide(user, str(uuid4()), {"action": "reject", "comment": "   "})
    assert caught.value.code == "TRANSFER_REASON_REQUIRED"
    database.assert_not_called()


def test_decision_trims_comment_and_forwards_action():
    user, client, request = principal([]), MagicMock(), str(uuid4())
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "decide", return_value={"status": "approved"}) as writer,
    ):
        service.decide(user, request, {"action": "approve", "comment": "  ok  "})
        service.decide(user, request, {"action": "start_review", "comment": ""})
    assert writer.call_args_list[0].args == (client, user["user_id"], TENANT, request, "approve", "ok")
    assert writer.call_args_list[1].args == (client, user["user_id"], TENANT, request, "start_review", None)


def test_reviewer_without_tenant_is_refused():
    user = principal([])
    user["institution_id"] = None
    with pytest.raises(AppError) as caught:
        service.reviews(user, True)
    assert caught.value.status_code == 403


@pytest.mark.parametrize("permissions", [[], ["departments.read"]])
def test_department_head_assignment_requires_department_management(permissions):
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError) as caught:
            service.assign_department_head(principal(permissions), str(uuid4()), str(uuid4()))
    assert caught.value.status_code == 403
    database.assert_not_called()


def test_department_head_assignment_revalidates_scope_and_calls_writer():
    user, client = principal(["departments.manage"]), MagicMock()
    department, faculty = str(uuid4()), str(uuid4())
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service, "validated_scope_permissions", return_value=["departments.manage"]) as scope,
        patch.object(service.repository, "assign_department_head", return_value={}) as writer,
    ):
        service.assign_department_head(user, department, faculty)
    scope.assert_called_once_with(client, user, TENANT)
    writer.assert_called_once_with(client, user["user_id"], TENANT, department, faculty)


@pytest.mark.parametrize(("code", "status", "public"), [
    ("P1102", 409, "TRANSFER_PLACEMENT_CHANGED"),
    ("P1105", 409, "TRANSFER_SECTION_FULL"),
    ("P1106", 409, "TRANSFER_ALREADY_OPEN"),
    ("23505", 409, "TRANSFER_ALREADY_OPEN"),
    ("P1110", 422, "DEPARTMENT_HEAD_INVALID"),
    ("P1111", 409, "STUDENT_HAS_OPEN_TRANSFER"),
    ("P1112", 422, "STUDENT_NO_PLACEMENT"),
    ("42501", 403, "FORBIDDEN"),
])
def test_database_failures_map_to_actionable_errors(code, status, public):
    failure = RuntimeError("private database context")
    failure.code = code
    with pytest.raises(AppError) as caught:
        service._call(lambda: (_ for _ in ()).throw(failure))
    assert (caught.value.status_code, caught.value.code) == (status, public)
    assert "private" not in caught.value.message


def test_direct_transfer_forwards_actor_tenant_and_chosen_student():
    user, client = principal([]), MagicMock()
    student, section = str(uuid4()), str(uuid4())
    with (
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "direct_transfer", return_value={"status": "approved"}) as writer,
    ):
        service.direct_transfer(user, {"student_id": student, "to_section_id": section, "reason": "Balance sizes"})
    writer.assert_called_once_with(client, user["user_id"], TENANT, student, section, "Balance sizes")
