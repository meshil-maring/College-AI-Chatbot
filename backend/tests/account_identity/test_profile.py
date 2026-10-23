from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.repositories.admin import admin_academics as identity
from app.schemas.students.student_profile import StudentProfile
from app.services.students import student_data

USER = "10000000-0000-0000-0000-000000000001"
TENANT = "20000000-0000-0000-0000-000000000001"
OTHER = "20000000-0000-0000-0000-000000000002"


def principal():
    return {"user_id": USER, "roles": ["student"], "institution_id": TENANT}


def student(**fields):
    return {
        "student_id": "30000000-0000-0000-0000-000000000001",
        "user_id": USER,
        "institution_id": TENANT,
        "student_number": "STU-1",
        "register_number": "REG-1",
        "university_roll_number": "ROLL-1",
        "email": "student@example.invalid",
        "approval_status": "approved",
        "status": "active",
        **fields,
    }


def test_profile_returns_only_account_identity_and_institution_labels():
    db = MagicMock()
    with (
        patch.object(
            identity, "get_student_by_user_id", return_value=student()
        ) as read,
        patch.object(
            student_data.tenancy,
            "get_institution_by_id",
            return_value={"name": "Quest", "code": "QUEST123"},
        ),
    ):
        result = student_data.get_own_profile(USER, client=db, current_user=principal())
    read.assert_called_once_with(db, USER)
    assert result.model_dump() == {
        "student_number": "STU-1",
        "register_number": "REG-1",
        "university_roll_number": "ROLL-1",
        "email": "student@example.invalid",
        "institution_name": "Quest",
        "institution_code": "QUEST123",
        "status": "active",
        "approval_status": "approved",
    }


def test_profile_rejects_foreign_tenant_before_reading_institution_labels():
    with (
        patch.object(
            identity,
            "get_student_by_user_id",
            return_value=student(institution_id=OTHER),
        ),
        patch.object(student_data.tenancy, "get_institution_by_id") as institution,
        pytest.raises(AppError) as error,
    ):
        student_data.get_own_profile(USER, client=MagicMock(), current_user=principal())
    assert error.value.status_code == 403
    assert error.value.code == "TENANT_MISMATCH"
    institution.assert_not_called()


def test_missing_account_profile_is_a_real_not_found():
    with (
        patch.object(identity, "get_student_by_user_id", return_value=None),
        pytest.raises(AppError) as error,
    ):
        student_data.get_own_profile(USER, client=MagicMock(), current_user=principal())
    assert error.value.code == "STUDENT_PROFILE_NOT_FOUND"


def test_identity_repository_does_not_select_retired_master_columns():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = student()
    assert identity.get_student_by_user_id(db, USER)["user_id"] == USER
    columns = db.table.return_value.select.call_args.args[0].split(",")
    assert {"user_id", "institution_id", "approval_status"}.issubset(columns)
    assert {"program_id", "academic_year_id", "semester_id"}.isdisjoint(columns)


def test_profile_contract_rejects_internal_identifiers_and_academic_fields():
    with pytest.raises(ValueError):
        StudentProfile(student_id=USER, program_id=OTHER)
