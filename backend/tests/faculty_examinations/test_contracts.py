"""Faculty examination contracts regressions with database doubles."""

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


def test_zero_and_absence_are_distinct():
    assert MarkInput(roster_id=ROSTER, mark_status='present', scored_marks=0).scored_marks == Decimal(0)
    for status in ('absent', 'exempt', 'not_attempted', 'missing'):
        assert MarkInput(roster_id=ROSTER, mark_status=status).scored_marks is None



@pytest.mark.parametrize('status,score', [('present', None), ('absent', 0), ('exempt', 0), ('missing', 0), ('unknown', None),
                                        ('present', -1), ('present', 'NaN'), ('present', 'Infinity'), ('present', '1.234')])
def test_invalid_mark_semantics(status, score):
    with pytest.raises(ValidationError):
        MarkInput(roster_id=ROSTER, mark_status=status, scored_marks=score)



@pytest.mark.parametrize('field', ['institution_id', 'faculty_id', 'student_id', 'course_id', 'section_id', 'actor', 'test_id', 'result_id', 'role', 'percentage'])
def test_mark_authority_fields_forbidden(field):
    with pytest.raises(ValidationError):
        MarkInput.model_validate({'roster_id': ROSTER, 'mark_status': 'absent', field: OTHER})



@pytest.mark.parametrize('extra', [{'max_marks': 0}, {'max_marks': 'NaN'}, {'passing_marks': 101}, {'passing_marks': -1},
                                 {'start_time': '12:00'}, {'start_time': '12:00', 'end_time': '11:00'},
                                 {'title': ''}, {'institution_id': TENANT}, {'status': 'PUBLISHED'}, {'created_by': ACTOR}])
def test_assessment_input_invariants(extra):
    with pytest.raises(ValidationError):
        AssessmentInput.model_validate({'title': 'Class Test', 'test_type': 'class_test', 'max_marks': 100, **extra})



def test_batch_and_correction_contracts():
    row = {'roster_id': ROSTER, 'mark_status': 'absent'}
    for rows in ([], [row, row], [row] * 501):
        with pytest.raises(ValidationError):
            MarksCommand(expected_version=1, rows=rows)
    with pytest.raises(ValidationError):
        Correction(expected_version=1, rows=[row], reason='')
    with pytest.raises(ValidationError):
        Transition(expected_version=0, action='lock')
    with pytest.raises(ValidationError):
        Transition(expected_version=1, action='force_publish')
