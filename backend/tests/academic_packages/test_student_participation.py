"""Package changes retire future obligations while retaining earned history."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.repositories.students import student_academic_experience as repository
from app.services.students import student_academic_experience as service
from app.services.students import student_context, student_results


@pytest.fixture
def experience(monkeypatch):
    context = {"student_id": "student", "institution_id": "tenant"}
    monkeypatch.setattr(student_context, "get_student_context", lambda _user: context)
    monkeypatch.setattr(student_context, "assert_student_context_tenant", lambda *_: None)
    rosters = [
        {"roster_id": "retired", "linked_student_id": "student",
         "institution_id": "tenant", "section_id": "old", "participation_active": False},
        {"roster_id": "current", "linked_student_id": "student",
         "institution_id": "tenant", "section_id": "core", "participation_active": True},
    ]
    rows = {
        "list_linked_rosters": rosters,
        "list_sections": [
            {"section_id": name, "course_offering_id": name, "code": name}
            for name in ("old", "core")
        ],
        "list_course_offerings": [
            {"course_offering_id": name, "course_id": name} for name in ("old", "core")
        ],
        "list_courses": [
            {"course_id": "old", "code": "A", "name": "Previous elective"},
            {"course_id": "core", "code": "DSA", "name": "Data structures"},
        ],
        "list_section_sessions": [
            {"session_id": "past", "institution_id": "tenant",
             "section_id": "old", "session_date": "2026-01-01"},
        ],
        "list_records_for_rosters": [
            {"session_id": "past", "roster_id": "retired", "status": "present"},
        ],
        "list_legacy_attendance": [],
        "list_test_types": {},
        # Return both even when the repository should narrow the query. The
        # service must also check section ownership before projecting a test.
        "list_faculty_tests": [
            {"institution_id": "tenant", "section_id": section, "title": section,
             "status": "SCHEDULED", "scheduled_date": datetime.now(UTC).date().isoformat()}
            for section in ("old", "core")
        ],
    }
    for name, value in rows.items():
        monkeypatch.setattr(repository, name, lambda *args, _value=value, **kwargs: _value)
    score = SimpleNamespace(
        course_code="A", course_name="Previous elective", test_name="Past quiz",
        conducted_at="2026-01-01", outcome="pass", mark_status="scored",
        scored_marks=8.0, max_marks=10.0, percentage=80.0,
    )
    monkeypatch.setattr(student_results, "get_own_test_results",
                        lambda *_args, **_kwargs: SimpleNamespace(records=[score]))
    monkeypatch.setattr(student_results, "get_own_results",
                        lambda *_args, **_kwargs: SimpleNamespace(records=[]))
    return rosters


def test_ended_subject_keeps_attendance_and_scores_but_has_no_upcoming_test(experience):
    attendance = service.get_subject_attendance({}, client=object())
    old = next(subject for subject in attendance.subjects if subject.subject_code == "A")
    assert old.classes_conducted == 1
    assert old.classes_present == 1
    upcoming = service.get_upcoming_assessments({}, client=object())
    assert [item.subject_code for item in upcoming.items] == ["DSA"]
    performance = service.get_subject_performance({}, client=object())
    old = next(subject for subject in performance.items if subject.subject_code == "A")
    assert old.assessments_completed == 1
    assert old.average_published_score == 80.0
    timeline = service.get_academic_timeline({}, client=object())
    assert any(item.title == "Past quiz" for item in timeline.items)
    assert not any(item.title == "old" for item in timeline.items)


def test_legacy_roster_without_participation_cache_remains_current(experience):
    experience[0].pop("participation_active")
    upcoming = service.get_upcoming_assessments({}, client=object())
    assert {item.subject_code for item in upcoming.items} == {"A", "DSA"}
