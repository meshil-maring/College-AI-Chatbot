"""Current academic screens exclude ended subjects while retaining history."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.services.faculty import assessment_roster
from app.services.faculty import faculty_attendance_reporting as reporting
from .test_contracts import ID, OTHER


class Query:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_): return self
    def eq(self, *_): return self
    def order(self, *_): return self
    def range(self, *_): return self
    def execute(self): return SimpleNamespace(data=self.rows)


def test_assessment_roster_omits_ended_memberships_without_losing_saved_marks():
    roster = [
        {"roster_id": ID, "roster_status": "ACTIVE", "participation_active": True},
        {"roster_id": OTHER, "roster_status": "ACTIVE", "participation_active": False},
        {"roster_id": "archived-marks", "roster_status": "ACTIVE", "participation_active": False},
    ]
    saved = [{"roster_id": "archived-marks", "mark_status": "present", "scored_marks": 50}]
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {}
    db.table.side_effect = lambda table: Query(roster if table == "faculty_attendance_rosters" else saved)
    test = {"section_id": ID, "can_manage": True, "status": "COMPLETED", "passing_marks": 40}
    result = assessment_roster.marks(
        {"institution_id": ID}, ID, db=db, t=test,
        identity_candidates=lambda *_: [], identity_match=lambda *_: (None, []),
        review=lambda rows: {"total": len(rows)},
    )
    assert {row["roster_id"] for row in result["rows"]} == {ID, "archived-marks"}
    assert result["rows"][1]["scored_marks"] == 50


def test_current_student_directory_hides_ended_membership_but_history_remains(monkeypatch):
    active = {"roster_id": ID, "register_number": "R1", "participation_active": True}
    ended = {"roster_id": OTHER, "register_number": "R2", "participation_active": False}
    history = {"roster_id": OTHER, "record_id": ID, "session_date": "2026-10-01", "status": "present"}
    monkeypatch.setattr(reporting, "section_data", lambda *_: ({}, [active, ended], [], [history]))
    page = reporting.students_page({"institution_id": ID}, UUID(ID))
    assert page["total"] == 1 and page["items"] == [active]
    monkeypatch.setattr(reporting, "get_admin_client", MagicMock)
    monkeypatch.setattr(reporting, "read_one", lambda *_: {"section_id": ID})
    profile = reporting.student_profile({"institution_id": ID}, UUID(OTHER))
    assert profile["student"] == ended and profile["history"] == [history]
