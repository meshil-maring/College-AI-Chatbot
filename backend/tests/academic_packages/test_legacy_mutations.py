"""Legacy routes use atomic DB writers and consistent academic eligibility."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest
from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.schemas.faculty.faculty_attendance import RosterStudentInput
from app.services.academics import legacy_rosters
from app.services.faculty import faculty_attendance as attendance
from .test_contracts import ID, OTHER

USER = {"user_id": ID, "institution_id": ID}


@pytest.mark.parametrize("field", ["program_id", "academic_year_id"])
def test_manual_roster_cannot_link_a_student_from_another_program_or_year(monkeypatch, field):
    db = MagicMock()
    monkeypatch.setattr(attendance, "get_admin_client", lambda: db)
    monkeypatch.setattr(attendance, "_assert_assigned", lambda *_: {
        "semester_id": ID, "program_id": ID, "academic_year_id": ID,
    })
    monkeypatch.setattr(attendance, "read_one", lambda *_: {"semester_number": 1})
    candidate = {"student_id": ID, "institution_id": ID, "register_number": "CSE001",
                 "program_id": ID, "academic_year_id": ID, field: OTHER}
    monkeypatch.setattr(attendance, "_identity_candidates", lambda *_: [candidate])
    with pytest.raises(AppError) as failure:
        attendance.create_manual(USER, UUID(ID), RosterStudentInput(register_number="CSE001", student_name="Ada"))
    assert failure.value.code == "IDENTITY_CONFLICT"
    db.table.return_value.insert.assert_not_called()


def test_atomic_assignment_uses_server_identity_and_returns_database_result():
    db = MagicMock()
    result = {"registration_id": OTHER, "roster_id": ID, "status": "assigned"}
    db.rpc.return_value.execute.return_value.data = result
    assert legacy_rosters.assign_subject(db, USER, ID, OTHER, "students.create") == result
    db.rpc.assert_called_once_with("assign_student_subject", {
        "p_actor_user_id": ID, "p_institution_id": ID, "p_section_id": ID,
        "p_registration_id": OTHER, "p_permission": "students.create",
    })
    db.table.assert_not_called()


def test_deletion_delegates_history_lock_check_delete_and_audit_to_one_rpc():
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {"roster_id": ID}
    assert legacy_rosters.delete_roster(db, USER, ID) == {"roster_id": ID}
    db.rpc.assert_called_once_with("delete_academic_roster", {
        "p_actor_user_id": ID, "p_institution_id": ID, "p_roster_id": ID,
    })
    db.table.assert_not_called()


@pytest.mark.parametrize("code,status", [("23503", 409), ("23514", 409), ("P0001", 409), ("42501", 403), ("PGRST202", 503)])
def test_deletion_failure_preserves_error_boundary_without_direct_delete(code, status):
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = APIError({"code": code, "message": "private SQL", "details": "", "hint": ""})
    with pytest.raises(AppError) as failure:
        legacy_rosters.delete_roster(db, USER, ID)
    assert failure.value.status_code == status and "private SQL" not in failure.value.message
    db.table.assert_not_called()
