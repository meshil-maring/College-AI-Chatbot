"""Employee profile request contracts mirror the database rules."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.admin.member_invitations import MemberInvitationCreate
from app.schemas.admin.member_profiles import (
    CommonProfile,
    FacultyProfile,
    MemberAdditionalDepartmentsWrite,
    MemberProfileWrite,
    StaffProfile,
)

DEPT_A = UUID("60000000-0000-0000-0000-000000000001")
DEPT_B = UUID("60000000-0000-0000-0000-000000000002")
COMMON = {"employee_id": " EMP-001 ", "phone": " +91 98765 43210 ", "designation": "  Assistant   Professor ",
          "joining_date": "2026-07-01"}
FACULTY = {"employment_type": "permanent", "employment_start_date": "2026-07-01",
           "qualification": "  ", "experience_years": 6.54}
STAFF = {"staff_category": "library", "employment_type": "contractual", "employment_start_date": "2026-06-01",
         "contract_end_date": "2027-05-31", "responsibilities": [" Issue desk ", "issue desk", "Catalogue"]}


def test_common_profile_is_normalized() -> None:
    common = CommonProfile(**COMMON)
    assert (common.employee_id, common.phone, common.designation) == (
        "EMP-001", "+91 98765 43210", "Assistant Professor")


@pytest.mark.parametrize("change", [
    {"employee_id": "EMP 001"}, {"employee_id": "-EMP"}, {"employee_id": "E" * 41},
    {"phone": "call me"}, {"designation": "   "}, {"joining_date": "soon"}, {"unknown": "x"},
])
def test_common_profile_rejects_invalid_fields(change) -> None:
    with pytest.raises(ValidationError):
        CommonProfile(**{**COMMON, **change})


def test_faculty_optional_text_and_experience_are_cleaned() -> None:
    faculty = FacultyProfile(**FACULTY)
    assert faculty.qualification is None and faculty.experience_years == 6.5


@pytest.mark.parametrize("model,data", [(FacultyProfile, FACULTY), (StaffProfile, STAFF)])
def test_non_permanent_employment_requires_an_ordered_contract_end(model, data) -> None:
    temporary = {**data, "employment_type": "temporary"}
    temporary.pop("contract_end_date", None)
    with pytest.raises(ValidationError, match="contract end date"):
        model(**temporary)
    with pytest.raises(ValidationError, match="cannot end before"):
        model(**{**temporary, "contract_end_date": "2020-01-01"})
    assert model(**{**temporary, "contract_end_date": "2027-12-31"}).contract_end_date is not None


def test_employment_types_are_role_specific() -> None:
    with pytest.raises(ValidationError):
        StaffProfile(**{**STAFF, "employment_type": "visiting"})
    assert FacultyProfile(**{**FACULTY, "employment_type": "visiting",
                             "contract_end_date": "2027-01-01"}).employment_type == "visiting"


def test_staff_responsibilities_are_trimmed_deduplicated_and_bounded() -> None:
    assert StaffProfile(**STAFF).responsibilities == ["Issue desk", "Catalogue"]
    for bad in ([], [" "], ["x" * 81], ["r"] * 21):
        with pytest.raises(ValidationError):
            StaffProfile(**{**STAFF, "responsibilities": bad})


def test_profile_has_exactly_one_role_section_and_a_flat_payload() -> None:
    with pytest.raises(ValidationError):
        MemberProfileWrite(common=COMMON)
    with pytest.raises(ValidationError):
        MemberProfileWrite(common=COMMON, faculty=FACULTY, staff=STAFF)
    profile = MemberProfileWrite(common=COMMON, staff=STAFF)
    payload = profile.database_payload()
    assert profile.role == "staff" and set(payload) == {"common", "staff"}
    assert payload["common"]["joining_date"] == "2026-07-01"


def test_invitation_profile_must_match_the_role_and_departments() -> None:
    base = {"email": "ada@example.com", "full_name": "Ada", "role": "faculty", "department_id": str(DEPT_A)}
    with pytest.raises(ValidationError, match="profile"):
        MemberInvitationCreate(**base)
    with pytest.raises(ValidationError, match="match the selected role"):
        MemberInvitationCreate(**base, profile={"common": COMMON, "staff": STAFF})
    with pytest.raises(ValidationError, match="primary department"):
        MemberInvitationCreate(**base, profile={"common": COMMON, "faculty": FACULTY},
                               additional_department_ids=[str(DEPT_A)])
    invited = MemberInvitationCreate(**base, profile={"common": COMMON, "faculty": FACULTY},
                                     additional_department_ids=[str(DEPT_B), str(DEPT_B)])
    stored = invited.database_profile()
    assert stored["additional_department_ids"] == [str(DEPT_B)]
    assert set(stored) == {"common", "faculty", "additional_department_ids"}


def test_additional_departments_are_bounded() -> None:
    with pytest.raises(ValidationError):
        MemberAdditionalDepartmentsWrite(department_ids=[UUID(int=i) for i in range(11)])
    assert MemberAdditionalDepartmentsWrite().department_ids == []
