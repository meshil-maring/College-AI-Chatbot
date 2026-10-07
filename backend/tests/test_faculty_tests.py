"""Assessment contracts; actual transactions and races are exercised in Docker."""

import struct
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.api.faculty_tests import faculty
from app.core.errors import AppError
from app.main import app
from app.schemas.faculty_tests import Correction, MarkInput, MarksCommand, Transition
from app.schemas.faculty_tests import TestInput as AssessmentInput
from app.services import faculty_tests as svc
from app.services import student_results
from app.services.authorization import effective_authorization
from app.services.faculty_attendance import ParsedRows

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
ACTOR = '33333333-3333-4333-8333-333333333333'
ROSTER = '44444444-4444-4444-8444-444444444444'
TEST = '55555555-5555-4555-8555-555555555555'
OTHER = '66666666-6666-4666-8666-666666666666'


def user():
    return {'user_id': ACTOR, 'institution_id': TENANT, 'status': 'active', 'roles': ['faculty'],
            'effective_permissions': ['results.read', 'results.manage'],
            'role_assignments': [{'role': 'faculty', 'scope_type': 'institution', 'scope_id': TENANT}]}


def roster(**extra):
    return {'roster_id': ROSTER, 'register_number': 'R1', 'university_roll_number': 'U1',
            'student_name': 'Student', 'roster_status': 'ACTIVE', 'reconciliation_state': 'LINKED', **extra}


def assessment(**extra):
    return {'test_id': TEST, 'section_id': SECTION, 'institution_id': TENANT, 'created_by': ACTOR,
            'status': 'COMPLETED', 'marks_state': 'DRAFT', 'max_marks': 100, 'passing_marks': 40, 'version': 3, **extra}


def teaching(**extra):
    return {'section_id': SECTION, 'faculty_user_id': ACTOR, 'institution_id': TENANT, 'is_active': True,
            'start_at': (datetime.now(UTC) - timedelta(days=1)).isoformat(), **extra}


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


@pytest.mark.parametrize('change', [{'section_id': OTHER}, {'institution_id': OTHER}, {'is_active': False}, {'revoked_at': '2026-01-01T00:00:00Z'},
                                  {'end_at': '2020-01-01T00:00:00Z'}, {'start_at': '2099-01-01T00:00:00Z'}, {'faculty_user_id': OTHER}])
def test_teaching_boundary_fails_closed(change):
    assert not effective_authorization(user(), {'section_id': SECTION, 'institution_id': TENANT}, 'results.manage',
                                       teaching=[teaching(**change)], responsibilities=[])


@pytest.mark.parametrize('kind,change,allowed', [
    ('department', {}, True), ('department', {'department_id': OTHER}, False),
    ('section', {}, True), ('section', {'section_code': 'B'}, False),
    ('section', {'program_id': OTHER}, False), ('section', {'semester_id': OTHER}, False),
    ('section', {'academic_year_id': OTHER}, False), ('department', {'institution_id': OTHER}, False),
])
def test_responsibility_monitoring_scope(kind, change, allowed):
    resource = {'institution_id': TENANT, 'section_id': SECTION, 'department_id': 'dept', 'program_id': 'program',
                'academic_year_id': 'year', 'semester_id': 'semester', 'section_code': 'A'}
    appointment = {**teaching(), **resource, 'scope_type': kind, 'permissions': ['results.read'], **change}
    assert effective_authorization(user(), resource, 'results.read', teaching=[], responsibilities=[appointment]) is allowed
    assert not effective_authorization(user(), resource, 'results.manage', teaching=[], responsibilities=[appointment])


def test_resource_capabilities_separate_monitoring_and_teaching(monkeypatch):
    sections = [{'section_id': SECTION, 'institution_id': TENANT}, {'section_id': OTHER, 'institution_id': TENANT}]
    monkeypatch.setattr(svc, '_active_sections', lambda _: sections)
    monkeypatch.setattr(svc, 'faculty_context', lambda _: {'teaching_assignments': [teaching()], 'responsibilities': []})
    assert svc.resources(user()) == [{**sections[0], 'can_manage': True}]


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


def test_present_statistics_preserve_non_present_states():
    stats = svc.calculate_review([
        {'mark_status': 'present', 'percentage': 0, 'outcome': 'fail'},
        {'mark_status': 'present', 'percentage': 100, 'outcome': 'pass'},
        {'mark_status': 'absent', 'percentage': None}, {'mark_status': 'exempt', 'percentage': None},
        {'mark_status': 'missing', 'percentage': None}, {'mark_status': 'not_attempted', 'percentage': None},
    ])
    assert stats == {'total': 6, 'entered': 5, 'missing': 1, 'absent': 1, 'exempt': 1, 'not_attempted': 1,
                     'conflicts': 0, 'pass': 1, 'fail': 1, 'average_percentage': 50.0}


def test_rpc_actor_tenant_are_always_server_derived(monkeypatch):
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {'saved': 1}
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    assert svc.rpc(user(), 'save_faculty_test_marks', {'p_actor': OTHER, 'p_tenant': OTHER}) == {'saved': 1}
    assert db.rpc.call_args.args[1]['p_actor'] == ACTOR
    assert db.rpc.call_args.args[1]['p_tenant'] == TENANT


@pytest.mark.parametrize('code,status', [('42501', 403), ('P0002', 404), ('40001', 409), ('23505', 409), ('23514', 422), ('23503', 422)])
def test_database_failures_are_mapped_without_schema_leaks(monkeypatch, code, status):
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = APIError({'code': code, 'message': 'internal schema details', 'details': None, 'hint': None})
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as caught:
        svc.rpc(user(), 'save_faculty_test', {})
    assert caught.value.status_code == status and 'internal schema' not in str(caught.value)


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


@pytest.fixture
def api():
    app.dependency_overrides[faculty] = user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(faculty, None)


@pytest.mark.parametrize('field', ['institution_id', 'faculty_id', 'student_id', 'section_id', 'role', 'test_id'])
def test_api_create_rejects_forged_authority(api, field):
    response = api.post(f'/api/v1/faculty/tests/sections/{SECTION}', json={'title': 'Test', 'test_type': 'internal', 'max_marks': 100, field: OTHER})
    assert response.status_code == 422


@pytest.mark.parametrize('method,path,payload', [
    ('get', f'/{TEST}', None), ('get', f'/{TEST}/history', None),
    ('post', f'/{TEST}/transition', {'expected_version': 1, 'action': 'publish'}),
    ('put', f'/{TEST}/marks', {'expected_version': 1, 'rows': [{'roster_id': ROSTER, 'mark_status': 'absent'}]}),
    ('post', f'/{TEST}/corrections', {'expected_version': 1, 'rows': [{'roster_id': ROSTER, 'mark_status': 'absent'}], 'reason': 'Verified correction'}),
])
def test_api_independently_denies_scope(api, monkeypatch, method, path, payload):
    def deny(*_args, **_kwargs):
        raise AppError('Scope denied', 403, 'FACULTY_SCOPE_DENIED')
    monkeypatch.setattr(svc, 'test_row', deny)
    response = api.request(method, '/api/v1/faculty/tests' + path, json=payload)
    assert response.status_code == 403


def test_unknown_or_foreign_test_is_not_disclosed(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(data=None)
    monkeypatch.setattr(svc, 'faculty_context', lambda _: {})
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as caught:
        svc.test_row(user(), OTHER)
    assert caught.value.status_code == 404


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

    from app.services.faculty_attendance import parse_attendance_file
    compound = MagicMock()
    compound.get_named_stream.return_value = struct.pack('<HH', opcode, 0)
    monkeypatch.setattr(xlrd.compdoc, 'CompDoc', lambda _: compound)
    reader = MagicMock()
    monkeypatch.setattr(xlrd, 'open_workbook', reader)
    with pytest.raises(AppError) as caught:
        parse_attendance_file('marks.xls', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', values_only=True)
    assert caught.value.code == 'UNSAFE_FORMULA'
    reader.assert_not_called()


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


def test_commit_revalidates_stored_rows_before_transaction(monkeypatch):
    monkeypatch.setattr(svc, 'review_import', lambda *_args, **_kwargs: {'test_id': TEST, 'rows': [{'raw_data': {'register_number': 'R1', 'mark_status': 'present', 'scored_marks': '101'}}]})
    monkeypatch.setattr(svc, 'marks', lambda *_: {'rows': [roster()], 'test': assessment()})
    write = MagicMock()
    monkeypatch.setattr(svc, 'rpc', write)
    with pytest.raises(AppError) as caught:
        svc.commit_import(user(), OTHER, SimpleNamespace(expected_version=3, expected_updated_at='stamp'))
    assert caught.value.code == 'IMPORT_REVIEW_REQUIRED'
    write.assert_not_called()


@pytest.mark.parametrize('race', [False, True])
def test_existing_roster_deletion_preserves_assessment_history(monkeypatch, race):
    from app.services import faculty_attendance
    db = MagicMock()
    monkeypatch.setattr(faculty_attendance, 'get_admin_client', lambda: db)
    monkeypatch.setattr(faculty_attendance, 'read_one', lambda _: {'section_id': SECTION})
    monkeypatch.setattr(faculty_attendance, '_assert_assigned', lambda *_: {})
    read = MagicMock(side_effect=[[], [] if race else [{'test_result_id': TEST}]])
    monkeypatch.setattr(faculty_attendance, 'read_rows', read)
    if race:
        db.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = APIError({'code': '23503', 'message': 'History FK', 'details': None, 'hint': None})
    with pytest.raises(AppError) as caught:
        faculty_attendance.delete_roster(user(), ROSTER)
    assert caught.value.code == 'ROSTER_HAS_HISTORY' and caught.value.status_code == 409
    if not race:
        db.table.return_value.delete.assert_not_called()
