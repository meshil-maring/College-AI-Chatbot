"""Non-network checks for complete plans and safe resumption of existing data."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from catalogue import PROGRAMS, calendar, seed_program
from writer import Writer


def test_complete_plan_can_be_repeated_without_creating_duplicate_records():
    client = MagicMock()
    writer = Writer(client, str(uuid4()), str(uuid4()), {})
    terms = calendar(writer, "DEMO")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(seed_program, writer, "DEMO", terms, item) for item in PROGRAMS]
        offerings = [item for future in futures for item in future.result()]
    created = deepcopy(writer.created)
    assert len(offerings) == 264
    assert len({item["offering_id"] for item in offerings}) == 264
    assert created["academic_sections"] == 88
    assert created["course_offerings"] == 132
    assert created["curriculum_versions"] == 6
    assert len(writer.operations) == 1067
    assert {row["course_type"] for row in writer.records["curriculum_subjects"].values()} == {
        "core", "elective", "open_elective", "skill", "project",
    }
    for specification in PROGRAMS:
        seed_program(writer, "DEMO", calendar(writer, "DEMO"), specification)
    assert writer.created == created
    assert len(writer.operations) == 1067
    client.rpc.assert_not_called()


@pytest.mark.parametrize("active,name", [(False, "Programming"), (True, "Changed name")])
def test_existing_inactive_or_incompatible_records_are_never_overwritten(active, name):
    client = MagicMock()
    department_id = str(uuid4())
    existing = {
        "course_id": str(uuid4()), "department_id": department_id,
        "code": "DEMO-CS101", "name": "Programming", "is_active": active,
    }
    writer = Writer(client, str(uuid4()), str(uuid4()), {"courses": [existing]}, apply=True)
    with pytest.raises(RuntimeError):
        writer.save("courses", {"department_id": department_id, "code": "DEMO-CS101", "name": name})
    client.rpc.assert_not_called()
