from unittest.mock import Mock
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.schemas.students.student_directory import StudentDirectoryResponse
from app.services.students import student_directory

TENANT = UUID("10000000-0000-0000-0000-000000000001")
PROGRAM = UUID("20000000-0000-0000-0000-000000000001")
ACTOR = {
    "user_id": "30000000-0000-0000-0000-000000000001",
    "institution_id": str(TENANT),
}


def response_data():
    return {
        "items": [
            {
                "record_id": "40000000-0000-0000-0000-000000000001",
                "record_type": "student",
                "student_name": "Ada Lovelace",
                "email": "ada@example.test",
                "register_number": "REG-1",
                "university_roll_number": None,
                "status": "signed_in",
                "approval_status": "approved",
                "account_status": "active",
                "student_status": "active",
                "is_active": True,
                "last_sign_in_at": "2026-10-28T10:00:00Z",
                "email_delivery_status": None,
                "expires_at": None,
                "program_id": str(PROGRAM),
                "program_name": "Computer Science",
                "program_code": "CS",
                "course_name": "B.Tech",
                "branch_name": "Engineering",
                "branch_code": "ENG",
                "batch_name": "2026-2030",
                "batch_code": "CS26",
                "admission_cohort_id": "60000000-0000-0000-0000-000000000001",
                "section_name": "Section A",
                "section_code": "A",
                "academic_section_id": "70000000-0000-0000-0000-000000000001",
                "created_at": "2026-10-01T10:00:00Z",
            }
        ],
        "total": 1,
        "limit": 25,
        "offset": 0,
        "summary": {"total": 1, "pending_sign_in": 0, "signed_in": 1, "no_signin": 0},
        "programs": [
            {
                "program_id": str(PROGRAM),
                "program_name": "Computer Science",
                "program_code": "CS",
            }
        ],
    }


def test_directory_contract_validates_academic_and_sign_in_fields():
    result = StudentDirectoryResponse.model_validate(response_data())

    assert result.items[0].status == "signed_in"
    assert result.items[0].program_id == PROGRAM
    assert result.summary.signed_in == 1


def test_directory_contract_accepts_rows_without_optional_placement_identifiers():
    response = response_data()
    response["items"][0].pop("admission_cohort_id")
    response["items"][0].pop("academic_section_id")

    result = StudentDirectoryResponse.model_validate(response)

    assert result.items[0].admission_cohort_id is None
    assert result.items[0].academic_section_id is None


def test_directory_requires_scoped_students_read(monkeypatch):
    monkeypatch.setattr(student_directory, "get_admin_client", lambda: object())
    monkeypatch.setattr(student_directory, "scope", lambda _: (str(TENANT), []))
    monkeypatch.setattr(student_directory, "validated_scope_permissions", lambda *_: [])
    read = Mock()
    monkeypatch.setattr(student_directory.repository, "read_directory", read)

    with pytest.raises(AppError) as error:
        student_directory.list_directory(
            ACTOR, search=None, status=None, program_id=None, limit=25, offset=0
        )

    assert error.value.code == "FORBIDDEN"
    read.assert_not_called()


def test_directory_passes_tenant_filters_and_pagination_to_repository(monkeypatch):
    client = object()
    read = Mock(return_value=response_data())
    monkeypatch.setattr(student_directory, "get_admin_client", lambda: client)
    monkeypatch.setattr(student_directory, "scope", lambda _: (str(TENANT), []))
    monkeypatch.setattr(
        student_directory, "validated_scope_permissions", lambda *_: ["students.read"]
    )
    monkeypatch.setattr(student_directory.repository, "read_directory", read)

    result = student_directory.list_directory(
        ACTOR,
        search="  Ada   Lovelace ",
        status="signed_in",
        program_id=PROGRAM,
        limit=10,
        offset=20,
    )

    assert result.total == 1
    read.assert_called_once_with(
        client,
        actor=ACTOR["user_id"],
        tenant=TENANT,
        search="Ada Lovelace",
        status="signed_in",
        program_id=PROGRAM,
        limit=10,
        offset=20,
    )


def test_directory_rejects_out_of_range_pagination(monkeypatch):
    monkeypatch.setattr(student_directory, "get_admin_client", lambda: object())
    monkeypatch.setattr(student_directory, "scope", lambda _: (str(TENANT), []))
    monkeypatch.setattr(
        student_directory, "validated_scope_permissions", lambda *_: ["students.read"]
    )
    read = Mock()
    monkeypatch.setattr(student_directory.repository, "read_directory", read)

    with pytest.raises(AppError) as error:
        student_directory.list_directory(
            ACTOR, search=None, status=None, program_id=None, limit=101, offset=0
        )

    assert error.value.code == "INVALID_PAGE"
    read.assert_not_called()


def test_admin_directory_route_requires_only_student_read():
    from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS

    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/students/directory")] == (
        "students.read",
    )
