"""Faculty examination marks regressions with database doubles."""

import struct
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.api.faculty.faculty_tests import faculty
from app.core.errors import AppError
from app.main import app
from app.schemas.faculty.faculty_tests import Correction, MarkInput, MarksCommand, Transition
from app.schemas.faculty.faculty_tests import TestInput as AssessmentInput
from app.services.faculty import faculty_tests as svc
from app.services.students import student_results
from app.services.auth.authorization import effective_authorization
from app.services.faculty.faculty_attendance import ParsedRows


from .support import TENANT, SECTION, ACTOR, ROSTER, TEST, OTHER, user, roster, assessment, teaching


def test_present_statistics_preserve_non_present_states():
    stats = svc.calculate_review([
        {'mark_status': 'present', 'percentage': 0, 'outcome': 'fail'},
        {'mark_status': 'present', 'percentage': 100, 'outcome': 'pass'},
        {'mark_status': 'absent', 'percentage': None}, {'mark_status': 'exempt', 'percentage': None},
        {'mark_status': 'missing', 'percentage': None}, {'mark_status': 'not_attempted', 'percentage': None},
    ])
    assert stats == {'total': 6, 'entered': 5, 'missing': 1, 'absent': 1, 'exempt': 1, 'not_attempted': 1,
                     'conflicts': 0, 'pass': 1, 'fail': 1, 'average_percentage': 50.0}



def test_student_projection_hides_foreign_unpublished_and_teacher_metadata(monkeypatch):
    monkeypatch.setattr(student_results.academics_repo, 'get_student_by_user_id', lambda *_: {'student_id': ROSTER, 'institution_id': TENANT})
    row = {'student_id': ROSTER, 'institution_id': TENANT, 'status': 'published', 'test_name': 'Assessment',
           'scored_marks': 0, 'max_marks': 100, 'mark_status': 'present', 'remarks': 'Teacher secret',
           'faculty_tests': {'status': 'LOCKED', 'passing_marks': 40}}
    monkeypatch.setattr(student_results.student_data_service, 'get_own_test_results', lambda *_args, **_kwargs: [
        row, {**row, 'student_id': OTHER}, {**row, 'institution_id': OTHER}, {**row, 'status': 'draft'},
        {**row, 'faculty_tests': {'status': 'COMPLETED'}},
    ])
    result = student_results.get_own_test_results({'user_id': ACTOR, 'institution_id': TENANT}, client=MagicMock()).model_dump()
    assert len(result['records']) == 1 and result['records'][0]['outcome'] == 'fail'
    for field in ('remarks', 'student_id', 'institution_id', 'test_id', 'faculty_tests'):
        assert field not in result['records'][0]



def test_marks_use_existing_identity_resolver_and_annotate_conflicts(monkeypatch):
    t = {**assessment(), 'section': {'program_id': 'program', 'academic_year_id': 'year'}, 'can_manage': True}
    monkeypatch.setattr(svc, 'test_row', lambda *_: t)
    db = MagicMock()
    roster_query, result_query = MagicMock(), MagicMock()
    roster_query.select.return_value.eq.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value.data = [roster(linked_student_id=OTHER)]
    result_query.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
    db.table.side_effect = lambda table: roster_query if table == 'faculty_attendance_rosters' else result_query
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    identity_lookup = MagicMock(return_value=[{'student_id': OTHER, 'institution_id': TENANT, 'register_number': 'R1', 'university_roll_number': 'U1', 'program_id': 'wrong', 'academic_year_id': 'year'}])
    monkeypatch.setattr(svc, '_identity_candidates', identity_lookup)
    data = svc.marks(user(), TEST)
    assert data['rows'][0]['reconciliation_state'] == 'CONFLICT'
    assert data['review']['conflicts'] == 1
    assert 'linked_student_id' not in data['rows'][0]
    identity_lookup.assert_called_once()



@pytest.mark.parametrize('history_error', ['P0001', '23503', '23514'])
def test_roster_delete_respects_atomic_history_rejection(monkeypatch, history_error):
    from app.services.faculty import faculty_attendance
    db = MagicMock()
    monkeypatch.setattr(faculty_attendance, 'get_admin_client', lambda: db)
    monkeypatch.setattr(faculty_attendance, 'read_one', lambda _: {'section_id': SECTION})
    monkeypatch.setattr(faculty_attendance, '_assert_assigned', lambda *_: {})
    db.rpc.return_value.execute.side_effect = APIError({
        'code': history_error, 'message': 'History protected', 'details': None, 'hint': None,
    })
    with pytest.raises(AppError) as caught:
        faculty_attendance.delete_roster(user(), ROSTER)
    assert caught.value.code == 'ROSTER_HAS_HISTORY' and caught.value.status_code == 409
    db.table.return_value.delete.assert_not_called()
