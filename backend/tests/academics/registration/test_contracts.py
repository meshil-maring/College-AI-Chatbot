from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.academics.semester_registration import ChoiceGroupWrite, SemesterSelection


def group_payload():
    return {
        "curriculum_version_id": str(uuid4()), "program_semester_id": str(uuid4()), "name": "Semester 3",
        "options": [
            {"name": "Option 1", "curriculum_subject_ids": [str(uuid4())]},
            {"name": "Option 2", "curriculum_subject_ids": [str(uuid4())]},
        ],
    }


def test_complete_options_validate_without_accepting_client_tenant():
    payload = group_payload()
    assert len(ChoiceGroupWrite.model_validate(payload).options) == 2
    with pytest.raises(ValidationError):
        ChoiceGroupWrite.model_validate({**payload, "institution_id": str(uuid4())})


@pytest.mark.parametrize("change", ["one-option", "empty-option", "duplicate-subject", "duplicate-name"])
def test_invalid_option_sets_are_rejected(change):
    payload = group_payload()
    if change == "one-option":
        payload["options"] = payload["options"][:1]
    elif change == "empty-option":
        payload["options"][0]["curriculum_subject_ids"] = []
    elif change == "duplicate-subject":
        payload["options"][0]["curriculum_subject_ids"] *= 2
    else:
        payload["options"][1]["name"] = " option 1 "
    with pytest.raises(ValidationError):
        ChoiceGroupWrite.model_validate(payload)


def test_student_cannot_supply_identity_or_individual_subjects():
    for field in ("student_id", "institution_id", "academic_offering_ids"):
        with pytest.raises(ValidationError):
            SemesterSelection.model_validate({"selected_option_ids": [], field: []})
    option = str(uuid4())
    with pytest.raises(ValidationError):
        SemesterSelection.model_validate({"selected_option_ids": [option, option]})
