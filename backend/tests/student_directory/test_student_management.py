from unittest.mock import Mock
from uuid import UUID

import pytest
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.students.student_directory import StudentProfileUpdateRequest
from app.services.students import student_management

TENANT = UUID("10000000-0000-0000-0000-000000000001")
STUDENT = UUID("40000000-0000-0000-0000-000000000001")
SECTION = UUID("50000000-0000-0000-0000-000000000001")
ACTOR = {
    "user_id": "30000000-0000-0000-0000-000000000001",
    "institution_id": str(TENANT),
}


def allow_management(monkeypatch, permissions):
    client = object()
    monkeypatch.setattr(student_management, "get_admin_client", lambda: client)
    monkeypatch.setattr(student_management, "scope", lambda _: (str(TENANT), []))
    monkeypatch.setattr(
        student_management, "validated_scope_permissions", lambda *_: permissions
    )
    return client


def test_profile_update_requires_course_permission_when_changing_section(monkeypatch):
    allow_management(monkeypatch, ["students.update"])
    update = Mock()
    monkeypatch.setattr(student_management.repository, "update_profile", update)

    with pytest.raises(AppError) as error:
        student_management.update_profile(
            ACTOR,
            STUDENT,
            {
                "student_name": "Ada Lovelace",
                "register_number": "REG-1",
                "university_roll_number": None,
                "academic_section_id": str(SECTION),
            },
        )

    assert error.value.code == "FORBIDDEN"
    update.assert_not_called()


def test_profile_update_passes_scoped_actor_and_validated_payload(monkeypatch):
    client = allow_management(monkeypatch, ["students.update"])
    result = {"student_id": str(STUDENT), "updated": True}
    update = Mock(return_value=result)
    monkeypatch.setattr(student_management.repository, "update_profile", update)
    payload = {
        "student_name": "Ada Lovelace",
        "register_number": "REG-1",
        "university_roll_number": None,
        "academic_section_id": None,
    }

    assert student_management.update_profile(ACTOR, STUDENT, payload) == result
    update.assert_called_once_with(
        client,
        actor=ACTOR["user_id"],
        tenant=TENANT,
        student=STUDENT,
        payload=payload,
    )


def test_state_and_delete_operations_use_distinct_student_permissions(monkeypatch):
    client = allow_management(monkeypatch, ["students.update", "students.delete"])
    set_active = Mock(return_value={"student_id": str(STUDENT), "is_active": False})
    delete = Mock(return_value={"student_id": str(STUDENT), "deleted": True})
    monkeypatch.setattr(student_management.repository, "set_active", set_active)
    monkeypatch.setattr(student_management.repository, "delete_profile", delete)

    assert student_management.set_active(ACTOR, STUDENT, False).is_active is False
    assert student_management.delete_profile(ACTOR, STUDENT).deleted is True
    set_active.assert_called_once_with(
        client, actor=ACTOR["user_id"], tenant=TENANT, student=STUDENT, active=False
    )
    delete.assert_called_once_with(
        client, actor=ACTOR["user_id"], tenant=TENANT, student=STUDENT
    )


def test_management_routes_have_explicit_permission_policies():
    from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS

    assert _ADMIN_ROUTE_PERMISSIONS[("PATCH", "/admin/students/{student_id}")] == (
        "students.update",
    )
    assert _ADMIN_ROUTE_PERMISSIONS[("POST", "/admin/students/{student_id}/deactivate")] == (
        "students.update",
    )
    assert _ADMIN_ROUTE_PERMISSIONS[("POST", "/admin/students/{student_id}/reactivate")] == (
        "students.update",
    )
    assert _ADMIN_ROUTE_PERMISSIONS[("DELETE", "/admin/students/{student_id}")] == (
        "students.delete",
    )


@pytest.mark.parametrize(
    ("code", "status", "public_code"),
    [
        ("23505", 409, "STUDENT_IDENTITY_EXISTS"),
        ("P1002", 409, "SECTION_CAPACITY"),
        ("P1004", 409, "STUDENT_REGISTRATION_LOCKED"),
        ("P2003", 409, "STUDENT_HAS_LINKED_RECORDS"),
        ("PGRST202", 503, "STUDENT_MANAGEMENT_SCHEMA_UNAVAILABLE"),
    ],
)
def test_database_errors_are_mapped_to_actionable_responses(code, status, public_code):
    failure = APIError({"code": code, "message": "private database detail"})

    with pytest.raises(AppError) as error:
        student_management._database(lambda: (_ for _ in ()).throw(failure))

    assert error.value.status_code == status
    assert error.value.code == public_code
    assert "private database detail" not in error.value.message


def test_profile_contract_trims_required_identity_and_normalizes_optional_roll():
    request = StudentProfileUpdateRequest.model_validate(
        {
            "student_name": "  Ada   Lovelace ",
            "register_number": " REG-1 ",
            "university_roll_number": "  ",
            "academic_section_id": None,
        }
    )

    assert request.student_name == "Ada Lovelace"
    assert request.register_number == "REG-1"
    assert request.university_roll_number is None


def test_profile_contract_rejects_unverified_email_changes():
    with pytest.raises(ValidationError):
        StudentProfileUpdateRequest.model_validate(
            {
                "student_name": "Ada Lovelace",
                "register_number": "REG-1",
                "university_roll_number": None,
                "academic_section_id": None,
                "email": "new@example.test",
            }
        )
