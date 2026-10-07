"""Attendance workflow regressions; database runtime checks live in SQL fixtures."""
import io
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.faculty_attendance import ManualAttendanceRequest, RosterUpdateRequest
from app.services import faculty_attendance as service
from app.services import faculty_attendance_extraction as extraction
from app.services import faculty_attendance_reporting as reporting
from app.services.authorization import effective_authorization

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
SEMESTER = '44444444-4444-4444-8444-444444444444'
ROSTER = '55555555-5555-4555-8555-555555555555'


def principal():
    return {'user_id': USER, 'institution_id': TENANT, 'status': 'active', 'roles': ['faculty'],
            'effective_permissions': ['attendance.read', 'attendance.manage'],
            'role_assignments': [{'role': 'faculty', 'scope_type': 'institution', 'scope_id': TENANT}]}


class Query:
    def __init__(self, table, rows): self.name = table; self.rows = rows; self.filters = []; self.bounds = None; self.single = False
    def select(self, *_args): return self
    def eq(self, key, value): self.filters.append(lambda r: str(r.get(key)) == str(value)); return self
    def in_(self, key, values): self.filters.append(lambda r: r.get(key) in values); return self
    def order(self, *_args, **_kwargs): return self
    def range(self, start, end): self.bounds = (start, end); return self
    def maybe_single(self): self.single = True; return self
    def execute(self):
        rows = [r for r in self.rows if all(f(r) for f in self.filters)]
        if self.bounds: rows = rows[self.bounds[0]: self.bounds[1] + 1]
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)


class Database:
    def __init__(self, tables): self.tables = tables
    def table(self, table): return Query(table, self.tables.get(table, []))


@pytest.mark.parametrize('row,candidates,expected,error', [
    ({'register_number': 'R1'}, [{'student_id': 's1', 'register_number': 'R1'}], 's1', False),
    ({'register_number': 'R1', 'university_roll_number': 'U1'}, [{'student_id': 's1', 'register_number': 'R1', 'university_roll_number': 'U1'}], 's1', False),
    ({'university_roll_number': 'U1'}, [{'student_id': 's1', 'university_roll_number': 'U1'}], 's1', False),
    ({'register_number': 'R1'}, [], None, False),
    ({'register_number': 'R1', 'university_roll_number': 'U2'}, [{'student_id': 's1', 'register_number': 'R1', 'university_roll_number': 'U1'}], None, True),
    ({'register_number': 'R2', 'university_roll_number': 'U1'}, [{'student_id': 's1', 'register_number': 'R1', 'university_roll_number': 'U1'}], None, True),
    ({'register_number': 'R1'}, [{'student_id': 's1', 'register_number': 'R1'}, {'student_id': 's2', 'register_number': 'R1'}], None, True),
    ({'register_number': 'R1', 'university_roll_number': 'U2'}, [{'student_id': 's1', 'register_number': 'R1'}, {'student_id': 's2', 'university_roll_number': 'U2'}], None, True),
])
def test_identity_matching_never_merges_ambiguous_or_conflicting_candidates(row, candidates, expected, error):
    student, errors = service.match_identity(TENANT, row, [{**s, 'institution_id': TENANT} for s in candidates])
    assert (student or {}).get('student_id') == expected
    assert bool(errors) is error


def test_cross_tenant_identifier_is_not_an_identity_candidate():
    assert service.match_identity(TENANT, {'register_number': 'R1'}, [{'student_id': 'secret', 'register_number': 'R1', 'institution_id': 'other'}]) == (None, [])


@pytest.fixture
def validator(monkeypatch):
    context = {'semester_id': SEMESTER, 'program_id': 'program', 'academic_year_id': 'year'}
    monkeypatch.setattr(service, '_assert_assigned', lambda *_args: context)
    db = Database({'semesters': [{'semester_id': SEMESTER, 'semester_number': 1}]})
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    return db


def test_first_semester_unregistered_identity_is_valid_without_roll(validator):
    summary, rows = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [{'register_number': 'R1', 'name': 'Ada', 'attendance': '70'}])
    assert summary['valid'] == 1 and rows[0]['student_id'] is None
    assert rows[0]['warnings'] and rows[0]['imported_summary'] == {'attendance': 70}


@pytest.mark.parametrize('change,issue', [
    ({'register_number': ''}, 'register_number is required'),
    ({'student_name': ''}, 'student_name is required'),
    ({'attendance': 'nan'}, 'finite'), ({'attendance': '101'}, 'between'),
    ({'classes_conducted': '2.5'}, 'whole number'),
    ({'classes_conducted': '2', 'classes_present': '2', 'classes_absent': '1'}, 'cannot exceed'),
    ({'attendance': ''}, 'required'), ({'student_name': '=WEBSERVICE("secret")'}, 'formula'),
    ({'institution_id': 'other'}, 'unexpected column'), ({'actor_id': USER}, 'unexpected column'),
    ({'status': 'unknown'}, 'status must'), ({'status': 'present'}, 'session_date'),
    ({'status': 'present', 'session_date': '2026-99-01'}, 'session_date'),
])
def test_import_row_errors_are_explicit_and_blocking(validator, change, issue):
    summary, rows = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [{'register_number': 'R1', 'student_name': 'Ada', 'attendance': '70', **change}])
    assert summary['valid'] == 0
    assert any(issue in e for e in rows[0]['errors'])


def test_duplicate_rows_and_later_semester_missing_roll_are_blocked(validator):
    row = {'register_number': 'R1', 'student_name': 'Ada', 'attendance': '70'}
    summary, _ = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [row, row])
    assert summary['duplicates'] == 1
    validator.tables['semesters'][0]['semester_number'] = 2
    summary, rows = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [row])
    assert summary['errors'] == 1 and 'university_roll_number' in rows[0]['errors'][0]


def test_empty_extraction_is_never_a_successful_zero_row_import(validator):
    summary, rows = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [])
    assert summary['errors'] == 1 and rows[0]['row_number'] == 1


def test_validation_detects_existing_linked_roster_conflict(validator):
    validator.tables['faculty_attendance_rosters'] = [{'institution_id': TENANT, 'section_id': SECTION,
        'roster_id': ROSTER, 'register_number': 'R1', 'linked_student_id': 'already-linked'}]
    summary, _ = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [{'register_number': 'R1', 'student_name': 'Ada', 'attendance': '70'}])
    assert summary['conflicts'] == 1


def test_pending_registration_is_supported_without_rejecting_attendance(validator):
    validator.tables['students'] = [{'institution_id': TENANT, 'student_id': 's1', 'register_number': 'R1', 'approval_status': 'pending'}]
    summary, rows = service.validate_rows(principal(), UUID(SECTION), UUID(SEMESTER), [{'register_number': 'R1', 'student_name': 'Ada', 'attendance': '70'}])
    assert summary['valid'] == 1 and rows[0]['student_id'] == 's1'


def test_attendance_edits_cannot_invent_active_registration(validator):
    validator.tables['faculty_attendance_rosters'] = [{'institution_id': TENANT, 'section_id': SECTION,
        'roster_id': ROSTER, 'roster_status': 'UNREGISTERED'}]
    with pytest.raises(AppError) as error:
        service.update_roster(principal(), UUID(ROSTER), RosterUpdateRequest(roster_status='ACTIVE'))
    assert error.value.code == 'REGISTRATION_STATE_MANAGED'


@pytest.mark.parametrize('content', [b'a,a\n1,2', b'a,b\n1,2,3', b'a\x00,b\n1,2', b'a,,b\n1,2,3'])
def test_malformed_csv_is_rejected(content):
    with pytest.raises(AppError): service.parse_attendance_file('input.csv', content)


def workbook(cell):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet r:id="r1" /></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml" /></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row>' + cell + '</row></sheetData></worksheet>')
    return output.getvalue()


def test_xlsx_inline_strings_and_formula_rejection():
    _, rows, ai = service.parse_attendance_file('input.xlsx', workbook('<c r="A1" t="inlineStr"><is><t>register_number</t></is></c>'))
    assert rows.headers == ('register_number',) and not ai
    with pytest.raises(AppError) as error:
        service.parse_attendance_file('input.xlsx', workbook('<c r="A1"><f>HYPERLINK("unsafe")</f><v>2</v></c>'))
    assert error.value.code == 'UNSAFE_FORMULA'


def test_xlsx_absolute_sheet_paths_and_complete_rows_are_supported():
    original = zipfile.ZipFile(io.BytesIO(workbook('')))
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as target:
        for name in original.namelist():
            data = original.read(name)
            if name.endswith('.rels'):
                data = data.replace(b'Target="worksheets', b'Target="/xl/worksheets')
            if name.endswith('sheet1.xml'):
                data = b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                for values in [('register_number','name','attendance'), ('R1','Ada','75')]:
                    data += b'<row>' + ''.join(f'<c r="{chr(65+i)}1" t="inlineStr"><is><t>{value}</t></is></c>' for i,value in enumerate(values)).encode() + b'</row>'
                data += b'</sheetData></worksheet>'
            target.writestr(name, data)
    _, rows, needs_ai = service.parse_attendance_file('openpyxl.xlsx', output.getvalue())
    assert rows == [{'register_number': 'R1', 'student_name': 'Ada', 'attendance': '75'}]
    assert needs_ai is False


def test_path_traversal_and_expansion_limits_in_workbooks(monkeypatch):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('../unsafe.xml', 'x')
    with pytest.raises(AppError): service.parse_attendance_file('unsafe.xlsx', output.getvalue())
    monkeypatch.setattr(service, 'MAX_UNPACKED_XLSX_BYTES', 1)
    with pytest.raises(AppError) as error: service.parse_attendance_file('expanded.xlsx', workbook(''))
    assert error.value.code == 'FILE_TOO_LARGE'


def test_unbounded_cell_addresses_are_rejected():
    with pytest.raises(AppError):
        service.parse_attendance_file('unsafe.xlsx', workbook('<c r="' + 'A' * 10000 + '1"><v>1</v></c>'))


def test_csv_limits_and_header_alias_duplicates():
    with pytest.raises(AppError): service.parse_attendance_file('a.csv', b'name,student_name\nA,B')
    with pytest.raises(AppError): service.parse_attendance_file('a.csv', b'register_number\n' + b'R1\n' * 501)


@pytest.mark.parametrize('filename', ['../x.csv', '..\\x.csv', 'a\x00.csv', 'c:x.csv', 'x\ny.csv'])
def test_unsafe_upload_names_are_rejected_before_parsing(monkeypatch, filename):
    monkeypatch.setattr(service, '_assert_assigned', lambda *_args: {})
    with pytest.raises(AppError) as error: service.upload_import(principal(), UUID(SECTION), UUID(SEMESTER), filename, b'x')
    assert error.value.code == 'UNSAFE_FILENAME'


def test_upload_mime_mismatch_and_ai_confirmation_are_enforced(monkeypatch):
    monkeypatch.setattr(service, '_assert_assigned', lambda *_args: {})
    with pytest.raises(AppError) as error:
        service.upload_import(principal(), UUID(SECTION), UUID(SEMESTER), 'x.csv', b'x', content_type='application/pdf')
    assert error.value.code == 'INVALID_MIME'
    from PIL import Image
    output = io.BytesIO()
    Image.new('RGB', (1, 1)).save(output, format='PNG')
    with pytest.raises(AppError) as error:
        service.upload_import(principal(), UUID(SECTION), UUID(SEMESTER), 'x.png', output.getvalue())
    assert error.value.code == 'AI_CONFIRMATION_REQUIRED'


def test_ai_output_schema_forbids_tenant_authority_and_requires_strings(monkeypatch):
    monkeypatch.setattr(extraction, 'ocr_text', lambda *_args: 'Unstructured attendance for R1 Ada')
    for answer in ['{"institution_id":"other","rows":[]}', '{"rows":[{"register_number":123}]}', '{"rows":[{"student_id":"secret"}]}']:
        monkeypatch.setattr(extraction, 'OpenRouterGenerationProvider', lambda answer=answer: SimpleNamespace(generate=lambda _ctx: SimpleNamespace(answer=answer)))
        with pytest.raises(AppError) as error: extraction.extract_attendance_rows(b'image', 'png')
        assert error.value.code == 'AI_EXTRACTION_INVALID'


def test_deterministic_ocr_table_does_not_invoke_ai(monkeypatch):
    monkeypatch.setattr(extraction, 'ocr_text', lambda *_args: 'register_number,name,attendance\nR1,Ada,70')
    provider = MagicMock()
    monkeypatch.setattr(extraction, 'OpenRouterGenerationProvider', provider)
    assert extraction.extract_attendance_rows(b'image', 'png')[0]['register_number'] == 'R1'
    provider.assert_not_called()


def test_missing_ocr_returns_actionable_error(monkeypatch):
    monkeypatch.setattr(extraction.shutil, 'which', lambda _name: None)
    with pytest.raises(AppError) as error: extraction.ocr_text(b'image', 'png')
    assert error.value.code == 'OCR_UNAVAILABLE'


def test_marking_uses_atomic_rpc_with_server_actor_and_tenant(monkeypatch):
    monkeypatch.setattr(service, '_assert_assigned', lambda *_args: {})
    db = MagicMock(); db.rpc.return_value.execute.return_value.data = {'session_id': 'session', 'record_count': 1}
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    service.mark_attendance(principal(), UUID(SECTION), ManualAttendanceRequest(session_date='2026-10-07', attendance={ROSTER: 'present'}))
    db.rpc.assert_called_once_with('mark_faculty_attendance', {'p_actor': USER, 'p_tenant': TENANT,
        'p_section_id': SECTION, 'p_session_date': '2026-10-07', 'p_attendance': {ROSTER: 'present'}, 'p_notes': None})
    db.table.assert_not_called()


@pytest.mark.parametrize('field', ['institution_id', 'actor_id', 'faculty_user_id', 'section_id'])
def test_marking_contract_rejects_forged_authorization_metadata(field):
    with pytest.raises(ValidationError): ManualAttendanceRequest(session_date='2026-10-07', attendance={ROSTER: 'present'}, **{field: TENANT})


def test_recorded_statistics_include_late_excused_and_ignore_imported_summary():
    assert reporting.statistics([{'status': x} for x in ['present','absent','late','excused']])['attendance_percentage'] == 25
    assert reporting.statistics([])['attendance_percentage'] is None
    assert not reporting.statistics([{'status': 'present'}] * 3 + [{'status': 'absent'}])['low_attendance']


def test_reporting_preserves_legacy_history_without_double_counting(monkeypatch):
    db = Database({'faculty_attendance_rosters': [{'institution_id': TENANT, 'section_id': SECTION, 'roster_id': ROSTER,
        'linked_student_id': 's1', 'register_number': 'R1', 'student_name': 'Ada', 'roster_status': 'ACTIVE'}],
        'faculty_attendance_sessions': [{'institution_id': TENANT, 'section_id': SECTION, 'session_id': 'session1', 'session_date': '2026-10-07'}],
        'faculty_attendance_records': [{'record_id': 'r1', 'roster_id': ROSTER, 'session_id': 'session1', 'status': 'present'}],
        'student_attendance': [{'student_attendance_id': 'a1', 'institution_id': TENANT, 'section_id': SECTION, 'student_id': 's1', 'date': '2026-10-07', 'status': 'present'},
            {'student_attendance_id': 'a2', 'institution_id': TENANT, 'section_id': SECTION, 'student_id': 's1', 'date': '2026-10-06', 'status': 'absent'}]})
    monkeypatch.setattr(reporting, 'get_admin_client', lambda: db)
    monkeypatch.setattr(reporting, 'authorize_section', lambda *_args: {'section_id': SECTION})
    summary = reporting.overview(principal(), UUID(SECTION))
    assert summary['session_count'] == 2 and summary['average_attendance'] == 50 and summary['record_count'] == 2
    page = reporting.students_page(principal(), UUID(SECTION), limit=1, search='Ada', low_only=True)
    assert page['total'] == 1 and page['items'][0]['record_count'] == 2
    profile = reporting.student_profile(principal(), UUID(ROSTER), limit=1)
    assert profile['total'] == 2 and len(profile['history']) == 1
    db.tables['faculty_attendance_rosters'][0]['reconciliation_state'] = 'CONFLICT'
    assert reporting.overview(principal(), UUID(SECTION))['record_count'] == 1


def test_new_resources_reuse_central_read_permissions_without_granting_mutations(monkeypatch):
    section = {'institution_id': TENANT, 'section_id': SECTION, 'department_id': 'dept'}
    position = {'faculty_user_id': USER, 'institution_id': TENANT, 'scope_type': 'department', 'department_id': 'dept',
                'start_at': '2000-01-01T00:00:00Z', 'permissions': ['attendance.read']}
    monkeypatch.setattr(reporting, 'faculty_context', lambda _u: {'teaching_assignments': [], 'responsibilities': [position]})
    monkeypatch.setattr(reporting, '_active_sections', lambda _t: [section, {**section, 'department_id': 'other'}])
    rows = reporting.resources(principal())
    assert len(rows) == 1 and rows[0]['can_manage'] is False
    assert not effective_authorization(principal(), section, 'attendance.manage', teaching=[], responsibilities=[position])


def test_migration_has_atomic_audit_identity_and_owner_guards():
    sql = (Path(__file__).resolve().parents[2] / 'supabase/migrations/20261012000000_faculty_attendance_workflow.sql').read_text(encoding='utf-8')
    assert 'CREATE TABLE' not in sql and 'DROP TABLE' not in sql
    for text in ['FOR UPDATE', 'pg_advisory_xact_lock', 'session.conducted_by <> p_actor', "'attendance.session.correct'",
                 "'attendance.import.commit'", "'attendance.identity.reconcile'", "reconciliation_state = 'CONFLICT'",
                 'raw_data = row', 'REVOKE ALL ON FUNCTION', 'ON CONFLICT(student_id, section_id, date) DO NOTHING']:
        assert text in sql


@pytest.mark.parametrize('path,method', [(f'/sections/{SECTION}/overview','get'), (f'/sections/{SECTION}/students','get'),
    (f'/sections/{SECTION}/sessions','get'), (f'/roster/{ROSTER}/profile','get')])
def test_api_forged_academic_resources_fail_safely(monkeypatch, path, method):
    from app.api import faculty as api
    from app.main import app
    monkeypatch.setattr(reporting, 'authorize_section', lambda *_args: (_ for _ in ()).throw(AppError('Denied', 403, 'FACULTY_SCOPE_DENIED')))
    monkeypatch.setattr(reporting, 'get_admin_client', lambda: Database({'faculty_attendance_rosters': []}))
    app.dependency_overrides[api._FACULTY] = principal
    try:
        response = getattr(TestClient(app), method)('/api/v1/faculty/attendance' + path)
        assert response.status_code in {403, 404}
    finally: app.dependency_overrides.pop(api._FACULTY, None)
