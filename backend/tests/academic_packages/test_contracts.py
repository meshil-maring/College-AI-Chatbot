"""Reject incomplete packages and forged identity before database access."""

import pytest
from pydantic import ValidationError

from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, DELEGABLE_STAFF_PERMISSIONS
from app.schemas.academics.academic_packages import validate_command

ID = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
PAYLOADS = {
    "save_curriculum": {"program_id": ID, "name": "CSE Curriculum", "code": "CSE202", "version": 1},
    "set_curriculum_subject": {"curriculum_id": ID, "course_id": ID, "study_semester": 1, "course_type": "core", "is_core": True},
    "save_package": {"curriculum_id": ID, "study_semester": 1, "name": "Data", "code": "CSE202-DEEBS", "curriculum_subject_ids": [ID, OTHER]},
    "save_class": {"program_id": ID, "batch_id": ID, "semester_id": ID, "study_semester": 1, "section_code": "A", "curriculum_id": ID, "student_choice_enabled": False},
    "set_class_package": {"class_id": ID, "package_id": ID, "enabled": True},
    "set_class_subject": {"class_id": ID, "curriculum_subject_id": ID, "section_id": ID},
    "prepare_class_teaching": {"class_id": ID},
    "set_class_responsibility": {"class_id": ID, "responsibility_id": ID, "enabled": True},
    "place_student": {"class_id": ID, "registration_id": ID},
    "assign_package": {"placement_id": ID, "package_id": ID},
    "change_package": {"assignment_id": ID, "package_id": ID, "expected_revision": 1, "reason": "Change specialization"},
    "request_change": {"assignment_id": ID, "package_id": ID, "reason": "Change specialization"},
    "review_request": {"request_id": ID, "approve": True, "reason": "Approved before cutoff"},
}


@pytest.mark.parametrize("operation", PAYLOADS)
def test_all_operations_validate_and_preserve_required_fields(operation):
    assert validate_command(operation, PAYLOADS[operation]) == PAYLOADS[operation]


@pytest.mark.parametrize("operation", PAYLOADS)
@pytest.mark.parametrize("field", ["institution_id", "actor_user_id", "student_id", "permissions"])
def test_clients_cannot_add_authoritative_fields(operation, field):
    with pytest.raises(ValidationError):
        validate_command(operation, {**PAYLOADS[operation], field: ID})


@pytest.mark.parametrize("operation,change", [
    ("save_curriculum", {"version": 0}), ("save_curriculum", {"version": True}),
    ("save_curriculum", {"name": "   "}), ("save_curriculum", {"code": "C" * 65}),
    ("set_curriculum_subject", {"study_semester": 0}),
    ("set_curriculum_subject", {"course_type": "unknown"}),
    ("save_package", {"curriculum_subject_ids": []}),
    ("save_package", {"curriculum_subject_ids": [ID, ID]}),
    ("save_class", {"student_choice_enabled": "true"}),
    ("save_class", {"change_cutoff": "2026-10-21T12:00:00"}),
    ("change_package", {"expected_revision": 0}),
    ("change_package", {"reason": "  "}),
    ("review_request", {"approve": 1}),
])
def test_invalid_commands_cannot_become_database_payloads(operation, change):
    with pytest.raises(ValidationError):
        validate_command(operation, {**PAYLOADS[operation], **change})


def test_cutoff_keeps_timezone_and_optional_defaults_remain_database_owned():
    payload = {**PAYLOADS["save_class"], "change_cutoff": "2026-10-21T12:00:00+05:30"}
    assert validate_command("save_class", payload)["change_cutoff"].endswith("+05:30")
    assert "change_cutoff" not in validate_command("save_class", PAYLOADS["save_class"])


def test_faculty_and_staff_receive_no_implicit_package_management_grants():
    for role in ("faculty", "staff", "super_admin"):
        assert not any(code.startswith("academic.package.") for code in DEFAULT_ROLE_PERMISSIONS[role])
    assert "academic.package.own.select" in DEFAULT_ROLE_PERMISSIONS["student"]
    assert "academic.package.change" in DELEGABLE_STAFF_PERMISSIONS
    assert "academic.curriculum.manage" not in DELEGABLE_STAFF_PERMISSIONS
