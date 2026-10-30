from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.academics import semester_registration as service
from ..support import TENANT, principal


@pytest.mark.parametrize("permissions", [[], ["courses.read"], ["students.update"], ["courses.manage"]])
def test_assignment_requires_academic_and_student_permissions_before_database(permissions):
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError) as caught:
            service.assign_student(principal(permissions), {})
    assert caught.value.status_code == 403
    database.assert_not_called()


@pytest.mark.parametrize("role", ["student", "staff", "faculty"])
def test_other_roles_cannot_configure_curriculum_choices(role):
    user = principal(["courses.manage"])
    user["roles"] = [role]
    user["role_assignments"][0]["role"] = role
    with patch.object(service, "get_admin_client") as database:
        with pytest.raises(AppError):
            service.save_group(user, {})
    database.assert_not_called()


def student_user(permissions):
    user = principal(permissions)
    user["roles"] = ["student"]
    user["role_assignments"][0]["role"] = "student"
    return user


def test_completion_derives_actor_and_tenant_from_approved_identity():
    user = student_user(["registration.own.manage"])
    registration_id, option_id = str(uuid4()), str(uuid4())
    context = {"student_id": str(uuid4()), "institution_id": TENANT}
    client = MagicMock()
    with (
        patch.object(service.student_context, "get_student_context", return_value=context),
        patch.object(service.student_context, "assert_student_context_tenant") as guard,
        patch.object(service, "get_admin_client", return_value=client),
        patch.object(service.repository, "complete", return_value={"status": "registered"}) as writer,
    ):
        assert service.complete(user, registration_id, [option_id])["status"] == "registered"
    guard.assert_called_once_with(user, context)
    writer.assert_called_once_with(client, user["user_id"], TENANT, registration_id, [option_id])


def test_read_only_student_cannot_register():
    user = student_user(["registration.own.read"])
    with (
        patch.object(service.student_context, "get_student_context", return_value={"institution_id": TENANT}),
        patch.object(service.student_context, "assert_student_context_tenant"),
        patch.object(service.repository, "complete") as writer,
    ):
        with pytest.raises(AppError):
            service.complete(user, str(uuid4()), [])
    writer.assert_not_called()


def test_capacity_failure_is_actionable_without_database_details():
    failure = RuntimeError("private database context")
    failure.code = "P1002"
    with pytest.raises(AppError) as caught:
        service._call(lambda: (_ for _ in ()).throw(failure))
    assert caught.value.status_code == 409
    assert caught.value.code == "REGISTRATION_CAPACITY"
    assert "private" not in caught.value.message
