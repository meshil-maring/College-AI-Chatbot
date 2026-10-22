"""Managed later-term teaching uses placement, while identity stays canonical."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.academics import managed_rosters
from app.services.faculty import assessment_roster
from app.services.faculty.attendance import validation
from app.services.faculty.attendance.identity import _identity_candidates, match_identity
from .test_contracts import ID, OTHER

TENANT = ID
SECTION = OTHER
STUDENT = "33333333-3333-4333-8333-333333333333"
SEMESTER = "44444444-4444-4444-8444-444444444444"
ROSTER = "55555555-5555-4555-8555-555555555555"
SCOPE = {"program_id": ID, "academic_year_id": OTHER, "semester_id": SEMESTER}


class Query:
    def __init__(self, rows): self.rows, self.filters, self.bounds, self.single = rows, [], None, False
    def select(self, *_): return self
    def eq(self, key, value): self.filters.append(lambda row: str(row.get(key)) == str(value)); return self
    def in_(self, key, values): self.filters.append(lambda row: row.get(key) in values); return self
    def order(self, *_args, **_kwargs): return self
    def range(self, start, end): self.bounds = (start, end); return self
    def maybe_single(self): self.single = True; return self
    def execute(self):
        rows = [row.copy() for row in self.rows if all(check(row) for check in self.filters)]
        if self.bounds: rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)


class Database:
    def __init__(self):
        self.student = {"student_id": STUDENT, "institution_id": TENANT, "program_id": ID,
                        "academic_year_id": ID, "register_number": "CSE001", "university_roll_number": "U001",
                        "approval_status": "approved", "is_active": True, "status": "active"}
        self.roster = {"roster_id": ROSTER, "institution_id": TENANT, "section_id": SECTION,
                       "register_number": "CSE001", "university_roll_number": "U001", "student_name": "Ada",
                       "roster_status": "ACTIVE", "reconciliation_state": "LINKED",
                       "linked_student_id": STUDENT, "participation_active": True}
        self.tables = {"students": [self.student], "faculty_attendance_rosters": [self.roster],
                       "semesters": [{"semester_id": SEMESTER, "semester_number": 1}]}
        self.context = {ROSTER: {**SCOPE, "student_id": STUDENT, "study_semester": 5}}
        self.calls = []

    def table(self, name): return Query(self.tables.get(name, []))
    def rpc(self, name, fields):
        assert name == "academic_package_roster_context"
        self.calls.append(fields)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=deepcopy(self.context)))


def marks(db):
    return assessment_roster.marks(
        {"institution_id": TENANT}, ID, db=db,
        t={"section_id": SECTION, "section": SCOPE, "can_manage": True,
           "status": "COMPLETED", "passing_marks": 40},
        identity_candidates=_identity_candidates, identity_match=match_identity,
        review=lambda rows: {"conflicts": sum(row["reconciliation_state"] == "CONFLICT" for row in rows)},
    )


def imported(db, **changes):
    row = {"register_number": "CSE001", "university_roll_number": "U001",
           "student_name": "Ada", "attendance": "80", **changes}
    return validation.validate_rows({"institution_id": TENANT}, UUID(SECTION), UUID(SEMESTER),
                                    [row], context=SCOPE, db=db)


def test_marks_accept_matching_managed_placement_in_later_year_without_rewriting_profile():
    db = Database()
    before = deepcopy(db.student)
    result = marks(db)
    assert result["review"]["conflicts"] == 0
    assert result["rows"][0]["reconciliation_state"] == "LINKED"
    assert db.student == before and db.student["academic_year_id"] == ID
    assert db.roster["linked_student_id"] == STUDENT
    assert db.calls == [{"p_tenant": TENANT, "p_roster_ids": [ROSTER]}]


def test_unmanaged_year_mismatch_remains_a_marking_conflict():
    db = Database()
    db.context = {}
    assert marks(db)["review"]["conflicts"] == 1


def test_managed_context_cannot_replace_the_canonical_student():
    db = Database()
    db.context[ROSTER]["student_id"] = OTHER
    assert marks(db)["review"]["conflicts"] == 1


def test_pending_later_term_identity_is_supported_without_approving_or_linking_it():
    db = Database()
    db.student["approval_status"] = "pending"
    db.roster.update(linked_student_id=None, roster_status="PENDING_APPROVAL", reconciliation_state="PENDING")
    before = deepcopy(db.student)
    result = marks(db)
    assert result["review"]["conflicts"] == 0
    assert result["rows"][0]["roster_status"] == "PENDING_APPROVAL"
    assert db.roster["linked_student_id"] is None and db.student == before


def test_attendance_import_accepts_explicit_later_term_placement_and_preserves_identity():
    db = Database()
    before = deepcopy(db.student)
    summary, rows = imported(db)
    assert summary["valid"] == 1 and rows[0]["student_id"] == STUDENT
    assert rows[0]["validation_status"] == "UPDATE"
    assert db.student == before


def test_later_study_semester_requires_roll_even_when_calendar_term_number_is_one():
    db = Database()
    db.student["university_roll_number"] = None
    db.roster["university_roll_number"] = None
    summary, rows = imported(db, university_roll_number="")
    assert summary["valid"] == 0
    assert any("university_roll_number" in error for error in rows[0]["errors"])


def test_unmanaged_year_mismatch_remains_an_import_conflict():
    db = Database()
    db.context = {}
    summary, rows = imported(db)
    assert summary["conflicts"] == 1
    assert rows[0]["student_id"] is None


def test_bulk_context_rejects_a_roster_outside_the_requested_ids():
    db = Database()
    db.context[OTHER] = db.context.pop(ROSTER)
    with pytest.raises(AppError) as failure:
        managed_rosters.contexts(db, TENANT, [db.roster])
    assert failure.value.code == "DATABASE_PROJECTION_INVALID"
