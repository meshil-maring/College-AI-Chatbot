"""Class registration must not enroll a student in any subject."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from postgrest.exceptions import APIError

from app.core.errors import AppError, app_error_handler
from app.schemas.students.student_registrations import StudentRegistrationCreate
from app.services.students import student_registrations as service

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
PROGRAM = '44444444-4444-4444-8444-444444444444'
YEAR = '55555555-5555-4555-8555-555555555555'
SEMESTER = '66666666-6666-4666-8666-666666666666'
BATCH = '77777777-7777-4777-8777-777777777777'
SCOPE = {'section_id': SECTION, 'program_id': PROGRAM, 'academic_year_id': YEAR,
         'semester_id': SEMESTER, 'section_code': 'A', 'code': 'A', 'course_id': 'subject', 'course_offering_id': 'offering'}


def principal():
    return {'user_id': USER, 'institution_id': TENANT, 'status': 'active', 'roles': ['faculty'],
            'effective_permissions': ['students.read', 'attendance.manage'],
            'role_assignments': [{'role': 'faculty', 'scope_type': 'institution', 'scope_id': TENANT}]}


def payload(**changes):
    return StudentRegistrationCreate(student_name='Ada Rao', register_number='CS001',
                                     batch_id=BATCH, email='ada@college.edu', **changes)


def stored(**changes):
    return {'registration_id': 'registration-1', 'batch_id': BATCH, 'institution_id': TENANT, 'program_id': PROGRAM,
            'academic_year_id': YEAR, 'semester_id': SEMESTER, 'section_code': 'A',
            'student_name': 'Ada Rao', 'register_number': 'CS001', 'university_roll_number': None,
            'batch_start_year': 2026, 'batch_end_year': 2030, 'created_by': USER, **changes}


class Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.bounds, self.inserted = db, table, [], None, None

    def select(self, *_args): return self
    def order(self, *_args, **_kwargs): return self
    def eq(self, key, value): self.filters.append(lambda row: str(row.get(key)) == str(value)); return self
    def in_(self, key, values): self.filters.append(lambda row: row.get(key) in values); return self
    def range(self, start, end): self.bounds = (start, end); return self
    def insert(self, data): self.inserted = data; return self

    def execute(self):
        self.db.reads.append(self.table)
        if self.db.error and self.table == 'student_registrations':
            raise self.db.error
        if self.inserted is not None:
            self.db.writes.append((self.table, self.inserted))
            row = {'registration_id': 'registration-1', **self.inserted}
            self.db.tables.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = [row for row in self.db.tables.get(self.table, []) if all(check(row) for check in self.filters)]
        if self.bounds:
            rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


class Database:
    def __init__(self):
        self.tables, self.reads, self.writes, self.error = {}, [], [], None

    def table(self, table): return Query(self, table)


@pytest.fixture
def database(monkeypatch):
    db = Database()
    db.tables['academic_batches'] = [{'batch_id': BATCH, 'institution_id': TENANT, 'program_id': PROGRAM, 'start_year': 2026, 'end_year': 2030, 'is_active': True}]
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    monkeypatch.setattr(service, '_assert_assigned', lambda *_args: SCOPE)
    monkeypatch.setattr(service, 'authorize_section', lambda *_args: SCOPE)
    return db


def test_registration_saves_admission_batch_and_class_without_any_subject_assignment(database):
    result = service.create_registration(principal(), UUID(SECTION), payload())
    assert result['batch_start_year'] == 2026 and result['batch_end_year'] == 2030
    assert result['program_id'] == PROGRAM and result['section_code'] == 'A'
    assert result['roster_status'] == 'UNREGISTERED' and result['linked_student_id'] is None
    assert len(database.writes) == 1
    table, data = database.writes[0]
    assert table == 'student_registrations'
    assert not {'course_id', 'course_offering_id', 'section_id', 'linked_student_id'} & data.keys()
    assert 'faculty_attendance_rosters' not in database.reads
    assert 'course_enrollments' not in database.reads


def test_batch_options_are_active_tenant_and_branch_scoped(database):
    saved = database.tables['academic_batches'][0]
    database.tables['academic_batches'].extend([
        {**saved, 'batch_id': 'foreign', 'institution_id': 'other'},
        {**saved, 'batch_id': 'other-branch', 'program_id': 'other'},
        {**saved, 'batch_id': 'archived', 'is_active': False},
    ])
    assert [batch['batch_id'] for batch in service.available_batches(principal(), UUID(SECTION))] == [BATCH]
    assert {batch['batch_id'] for batch in service.available_batches(principal(), UUID(SECTION), include_inactive=True)} == {BATCH, 'archived'}


def test_batch_and_search_filters_apply_before_class_registration_pagination(database):
    database.tables['student_registrations'] = [stored(registration_id='other-batch', batch_id='other'),
        stored(registration_id='r2', register_number='CS002', student_name='Ben Rao'),
        stored(registration_id='r3', register_number='CS003', student_name='Ada Shah'),
        stored(registration_id='foreign', register_number='CS004', institution_id='other')]
    result = service.list_registrations(principal(), UUID(SECTION), batch_id=UUID(BATCH), search='ada', limit=1)
    assert result['total'] == 1 and result['items'][0]['registration_id'] == 'r3'
    result = service.list_registrations(principal(), UUID(SECTION), batch_id=UUID(BATCH), sort='student_name', limit=1, offset=1)
    assert result['total'] == 2 and result['items'][0]['student_name'] == 'Ben Rao'
    assert service.list_registrations(principal(), UUID(SECTION), batch_id=UUID(USER))['total'] == 0


@pytest.mark.parametrize('changes', [{'institution_id': 'other'}, {'program_id': 'other'}, {'is_active': False}])
def test_registration_cannot_use_a_foreign_or_archived_batch(database, changes):
    database.tables['academic_batches'][0].update(changes)
    with pytest.raises(AppError) as error:
        service.create_registration(principal(), UUID(SECTION), payload())
    assert error.value.code == 'BATCH_UNAVAILABLE'
    assert not database.writes


def test_existing_account_is_matched_without_changing_approval_or_creating_auth_identity(database):
    database.tables['students'] = [{'student_id': 'student-1', 'institution_id': TENANT, 'register_number': 'CS001',
                                   'program_id': PROGRAM, 'approval_status': 'pending'}]
    result = service.create_registration(principal(), UUID(SECTION), payload())
    assert result['roster_status'] == 'PENDING_APPROVAL'
    assert database.tables['students'][0]['approval_status'] == 'pending'
    assert [table for table, _data in database.writes] == ['student_registrations']


@pytest.mark.parametrize('student', [
    {'register_number': 'CS001', 'program_id': 'other-program'},
    {'register_number': 'CS001', 'university_roll_number': 'U2'},
])
def test_registration_rejects_branch_and_identifier_conflicts_without_writing(database, student):
    database.tables['students'] = [{'student_id': 'student-1', 'institution_id': TENANT, **student}]
    with pytest.raises(AppError) as error:
        service.create_registration(principal(), UUID(SECTION), payload(university_roll_number='U1'))
    assert error.value.code == 'IDENTITY_CONFLICT'
    assert not database.writes


def test_denied_or_expired_scope_is_checked_before_reading_or_writing(monkeypatch, database):
    def denied(*_args): raise AppError('Assignment expired', 403, 'FACULTY_SCOPE_DENIED')
    monkeypatch.setattr(service, '_assert_assigned', denied)
    monkeypatch.setattr(service, 'authorize_section', denied)
    with pytest.raises(AppError): service.create_registration(principal(), UUID(SECTION), payload())
    with pytest.raises(AppError): service.list_registrations(principal(), UUID(SECTION))
    with pytest.raises(AppError): service.available_batches(principal(), UUID(SECTION))
    assert not database.reads and not database.writes


def test_class_list_cannot_mix_tenants_branches_terms_or_section_codes(database):
    database.tables['student_registrations'] = [stored(), stored(registration_id='foreign-tenant', institution_id='other'),
        stored(registration_id='foreign-branch', program_id='other'), stored(registration_id='foreign-year', academic_year_id='other'),
        stored(registration_id='foreign-semester', semester_id='other'), stored(registration_id='foreign-section', section_code='B')]
    result = service.list_registrations(principal(), UUID(SECTION))
    assert result['total'] == 1 and result['items'][0]['registration_id'] == 'registration-1'


def test_current_approval_status_is_resolved_before_filtering_and_pagination(database):
    database.tables['student_registrations'] = [stored(), stored(registration_id='r2', register_number='CS002')]
    database.tables['students'] = [{'student_id': 's2', 'institution_id': TENANT, 'register_number': 'CS002', 'approval_status': 'pending'}]
    result = service.list_registrations(principal(), UUID(SECTION), limit=1, registration='PENDING_APPROVAL')
    assert result['total'] == 1 and result['items'][0]['registration_id'] == 'r2'
    database.tables['students'][0].update(approval_status='approved', is_active=True, status='active')
    result = service.list_registrations(principal(), UUID(SECTION), registration='ACTIVE')
    assert result['total'] == 1 and result['items'][0]['linked_student_id'] == 's2'


def test_duplicates_and_missing_migration_are_safe_client_errors(database):
    database.error = APIError({'code': '23505', 'message': 'private constraint name', 'details': '', 'hint': ''})
    with pytest.raises(AppError) as error:
        service.create_registration(principal(), UUID(SECTION), payload())
    assert error.value.code == 'REGISTRATION_DUPLICATE' and 'private' not in error.value.message
    database.error = APIError({'code': 'PGRST205', 'message': 'student_registrations not found', 'details': '', 'hint': ''})
    with pytest.raises(AppError) as error:
        service.list_registrations(principal(), UUID(SECTION))
    assert error.value.status_code == 503


def test_class_registration_appears_in_history_before_any_subject_membership(monkeypatch, database):
    from app.services.faculty import faculty_students
    monkeypatch.setattr(faculty_students, 'get_admin_client', lambda: database)
    monkeypatch.setattr(faculty_students, 'authorize_section', lambda *_args: SCOPE)
    database.tables['student_registrations'] = [stored(created_at='2026-10-20T08:00:00Z'),
        stored(registration_id='foreign', section_code='B', created_at='2026-10-20T08:00:00Z')]
    result = faculty_students.registration_history(principal(), UUID(SECTION), search='CS001')
    assert result['total'] == 1
    assert result['items'][0]['action'] == 'class_registered'
    assert result['items'][0]['registration_id'] == 'registration-1'
    assert not database.writes


@pytest.mark.parametrize('data', [
    {'batch_start_year': 2030, 'batch_end_year': 2026}, {'batch_start_year': 2026, 'batch_end_year': 2026},
    {'batch_start_year': 2026, 'batch_end_year': 2040}, {'batch_start_year': 1800, 'batch_end_year': 1804},
    {'batch_start_year': 2026, 'batch_end_year': 2030, 'course_id': SECTION},
    {'batch_start_year': 2026, 'batch_end_year': 2030, 'program_id': PROGRAM},
])
def test_cohort_and_server_owned_placement_are_validated(data):
    with pytest.raises(ValidationError):
        StudentRegistrationCreate(student_name='Ada', register_number='R1', batch_id=BATCH, **data)


def test_registration_routes_validate_payloads_and_reuse_authenticated_scope(monkeypatch, database):
    from app.api.faculty import faculty
    import app.repositories.admin.admin_audit as audit
    app = FastAPI()
    app.include_router(faculty.router, prefix='/api/v1')
    app.add_exception_handler(AppError, app_error_handler)
    app.dependency_overrides[faculty._FACULTY] = principal
    monkeypatch.setattr(audit, 'record_admin_action', lambda *_args: {})
    client = TestClient(app)
    path = f'/api/v1/faculty/student-registrations/sections/{SECTION}'
    assert client.post(path, json={'student_name': 'Ada', 'register_number': 'R1'}).status_code == 422
    response = client.post(path, json=payload().model_dump(mode='json'))
    assert response.status_code == 201
    assert response.json()['subjects_assigned'] is False
    assert client.get(path).json()['total'] == 1
    assert [batch['batch_id'] for batch in client.get(path + '/batches').json()] == [BATCH]
    assert client.get(path + f'?batch_id={BATCH}&search=ada').json()['total'] == 1
    assert client.get(path + f'?batch_id={USER}').json()['total'] == 0
    database.tables['academic_batches'][0]['is_active'] = False
    assert client.get(path + '/batches').json() == []
    assert client.get(path + '/batches?include_inactive=true').json()[0]['batch_id'] == BATCH
