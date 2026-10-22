"""Faculty examination imports regressions with database doubles."""

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


@pytest.mark.parametrize('change,state', [
    ({}, 'VALID'), ({'scored_marks': '0'}, 'VALID'), ({'scored_marks': '-1'}, 'ERROR'),
    ({'scored_marks': '101'}, 'ERROR'), ({'scored_marks': '1.234'}, 'ERROR'), ({'scored_marks': 'NaN'}, 'ERROR'),
    ({'scored_marks': '1e2'}, 'ERROR'), ({'scored_marks': '=SUM(1)'}, 'ERROR'), ({'scored_marks': ''}, 'ERROR'),
    ({'mark_status': 'absent', 'scored_marks': ''}, 'VALID'), ({'mark_status': 'absent', 'scored_marks': '0'}, 'ERROR'),
    ({'mark_status': 'exempt', 'scored_marks': ''}, 'VALID'), ({'mark_status': 'not_attempted', 'scored_marks': ''}, 'VALID'),
    ({'mark_status': 'missing', 'scored_marks': ''}, 'ERROR'), ({'mark_status': 'bad'}, 'ERROR'),
    ({'register_number': 'foreign'}, 'ERROR'), ({'register_number': ''}, 'ERROR'),
    ({'university_roll_number': 'wrong'}, 'CONFLICT'), ({'remarks': '@WEBSERVICE()'}, 'ERROR'),
])
def test_import_validation(change, state):
    _, rows = svc.validate_import([{'register_number': 'R1', 'mark_status': 'present', 'scored_marks': '75', **change}], [roster()], 100)
    assert rows[0]['validation_status'] == state
    assert bool(rows[0]['errors']) == (state not in {'VALID'})



@pytest.mark.parametrize('state', ['UNREGISTERED', 'PENDING_APPROVAL'])
def test_import_preserves_unregistered_roster_with_warning(state):
    summary, rows = svc.validate_import([{'register_number': 'R1', 'mark_status': 'absent'}], [roster(roster_status=state)], 100)
    assert summary['valid'] == summary['warnings'] == 1
    assert rows[0]['warnings'] and 'student_id' not in rows[0]



def test_import_duplicates_and_conflicts():
    raw = {'register_number': 'R1', 'mark_status': 'absent'}
    _, rows = svc.validate_import([raw, raw], [roster()], 100)
    assert rows[1]['validation_status'] == 'DUPLICATE'
    _, rows = svc.validate_import([raw], [roster(reconciliation_state='CONFLICT')], 100)
    assert rows[0]['validation_status'] == 'CONFLICT'



@pytest.mark.parametrize('field', ['institution_id', 'student_id', 'test_id', 'result_id', 'import_id', 'roster_id', 'faculty_id', 'percentage'])
def test_import_cannot_select_authority(field):
    with pytest.raises(AppError, match='Use register_number'):
        svc.validate_import([{'register_number': 'R1', 'mark_status': 'absent', field: OTHER}], [roster()], 100)



def test_empty_spreadsheet_headers_still_checked():
    with pytest.raises(AppError):
        svc.validate_import(ParsedRows(headers=['register_number', 'mark_status']), [roster()], 100)



def test_upload_uses_deterministic_reader_and_reuses_staging(monkeypatch):
    monkeypatch.setattr(svc, 'test_row', lambda *_args, **_kwargs: assessment())
    monkeypatch.setattr(svc, 'marks', lambda *_: {'rows': [roster()]})
    spy = MagicMock(return_value={'import_id': OTHER})
    monkeypatch.setattr(svc, 'rpc', spy)
    monkeypatch.setattr(svc, 'review_import', lambda *_: {'import_id': OTHER})
    result = svc.upload_import(user(), TEST, 'marks.csv', b'register_number,mark_status,scored_marks\nR1,present,0\n', 'text/csv')
    assert result['import_id'] == OTHER
    assert spy.call_args.args[1] == 'stage_faculty_test_import'
    assert spy.call_args.args[2]['p_rows'][0]['normalized_data']['scored_marks'] == '0'



@pytest.mark.parametrize('name,mime,content', [('..\\marks.csv', 'text/csv', b'a'), ('marks.csv', 'image/png', b'a'),
                                            ('marks.xlsx', None, b'wrong'), ('marks.pdf', 'application/pdf', b'%PDF')])
def test_upload_security_reuses_attendance_checks(monkeypatch, name, mime, content):
    monkeypatch.setattr(svc, 'test_row', lambda *_args, **_kwargs: assessment())
    with pytest.raises(AppError):
        svc.upload_import(user(), TEST, name, content, mime)



@pytest.mark.parametrize('opcode', [0x0006, 0x0206, 0x0406, 0x0221, 0x04BC])
def test_binary_xls_formula_records_are_rejected(monkeypatch, opcode):
    import xlrd
    import xlrd.compdoc

    from app.services.faculty.faculty_attendance import parse_attendance_file
    compound = MagicMock()
    compound.get_named_stream.return_value = struct.pack('<HH', opcode, 0)
    monkeypatch.setattr(xlrd.compdoc, 'CompDoc', lambda _: compound)
    reader = MagicMock()
    monkeypatch.setattr(xlrd, 'open_workbook', reader)
    with pytest.raises(AppError) as caught:
        parse_attendance_file('marks.xls', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', values_only=True)
    assert caught.value.code == 'UNSAFE_FORMULA'
    reader.assert_not_called()



def test_commit_revalidates_stored_rows_before_transaction(monkeypatch):
    monkeypatch.setattr(svc, 'review_import', lambda *_args, **_kwargs: {'test_id': TEST, 'rows': [{'raw_data': {'register_number': 'R1', 'mark_status': 'present', 'scored_marks': '101'}}]})
    monkeypatch.setattr(svc, 'marks', lambda *_: {'rows': [roster()], 'test': assessment()})
    write = MagicMock()
    monkeypatch.setattr(svc, 'rpc', write)
    with pytest.raises(AppError) as caught:
        svc.commit_import(user(), OTHER, SimpleNamespace(expected_version=3, expected_updated_at='stamp'))
    assert caught.value.code == 'IMPORT_REVIEW_REQUIRED'
    write.assert_not_called()
