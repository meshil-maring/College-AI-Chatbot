"""Admin shares Faculty Students behavior without changing Staff or Faculty roles."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import admin
from app.core.security import get_current_user
from app.main import app
from app.services import authorization, faculty_responsibilities, faculty_students, student_registrations
from app.services import faculty_attendance_reporting as reporting

TENANT = '11111111-1111-4111-8111-111111111111'
FOREIGN = '11111111-1111-4111-8111-111111111112'
SECTION = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
PROGRAM = '44444444-4444-4444-8444-444444444444'
YEAR = '55555555-5555-4555-8555-555555555555'
SEMESTER = '66666666-6666-4666-8666-666666666666'
BATCH = '77777777-7777-4777-8777-777777777777'
ROSTER = '88888888-8888-4888-8888-888888888888'
BASE = '/api/v1/admin/student-workspace'
SCOPE = {'institution_id': TENANT, 'section_id': SECTION, 'program_id': PROGRAM, 'academic_year_id': YEAR,
         'semester_id': SEMESTER, 'code': 'A', 'section_code': 'A', 'name': 'Section A',
         'course_id': 'subject', 'course': {'name': 'Data Mining', 'code': 'CS501'}}
PAYLOAD = {'student_name': 'Ada Rao', 'register_number': 'CS001', 'batch_id': BATCH}


class Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.bounds, self.inserted, self.single = db, table, [], None, None, False
    def select(self, *_): return self
    def order(self, *_args, **_kwargs): return self
    def eq(self, key, value):
        self.filters.append(lambda row: str(row.get('record_data', {}).get(key.split('->>')[1])) == str(value) if '->>' in key else str(row.get(key)) == str(value))
        return self
    def in_(self, key, values): self.filters.append(lambda row: row.get(key) in values); return self
    def range(self, start, end): self.bounds = (start, end); return self
    def maybe_single(self): self.single = True; return self
    def insert(self, data): self.inserted = data; return self
    def execute(self):
        self.db.reads.append(self.table)
        if self.inserted is not None:
            self.db.writes.append((self.table, self.inserted))
            row = {'registration_id': 'registration-1', 'created_at': '2026-10-20T08:00:00Z', **self.inserted}
            self.db.tables.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = [row for row in self.db.tables.get(self.table, []) if all(test(row) for test in self.filters)]
        if self.bounds: rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=(rows[0] if rows else None) if self.single else rows)


class Database:
    def __init__(self): self.tables, self.reads, self.writes = {}, [], []
    def table(self, name): return Query(self, name)


@pytest.fixture
def api(monkeypatch):
    user = {'user_id': USER, 'status': 'active', 'roles': ['admin'], 'institution_id': FOREIGN,
            'permissions_resolved': True, 'effective_permissions': ['students.read', 'students.create', 'attendance.read'],
            'role_assignments': [{'role': 'admin', 'scope_type': 'institution', 'scope_id': TENANT, 'is_active': True}]}
    db = Database()
    db.tables['academic_batches'] = [{'batch_id': BATCH, 'institution_id': TENANT, 'program_id': PROGRAM,
                                     'start_year': 2026, 'end_year': 2030, 'is_active': True}]
    db.tables['faculty_attendance_rosters'] = [{'institution_id': TENANT, 'section_id': SECTION, 'roster_id': ROSTER,
        'register_number': 'CS002', 'student_name': 'Ben Rao', 'university_roll_number': None, 'email': None,
        'roster_status': 'PENDING_APPROVAL', 'linked_student_id': None, 'created_at': '2026-10-19T08:00:00Z'}]
    for module in (admin, authorization, student_registrations, reporting, faculty_students, faculty_responsibilities):
        monkeypatch.setattr(module, 'get_admin_client', lambda: db)
    monkeypatch.setattr(authorization.tenancy_repo, 'get_institution_by_id', lambda *_: {'status': 'active', 'is_active': True})
    monkeypatch.setattr(admin, '_active_sections', lambda tenant: [SCOPE] if str(tenant) == TENANT else [])
    monkeypatch.setattr(faculty_responsibilities, '_active_sections', admin._active_sections)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(app), db, user
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_admin_without_a_teaching_assignment_can_register_and_read_saved_class_records(api):
    client, db, _ = api
    sections = client.get(BASE + '/sections').json()
    assert sections[0]['institution_id'] == TENANT and sections[0]['can_manage'] is True
    response = client.post(f'{BASE}/sections/{SECTION}/registrations?institution_id={FOREIGN}', json=PAYLOAD)
    assert response.status_code == 201, response.text
    assert response.json()['batch_start_year'] == 2026 and response.json()['subjects_assigned'] is False
    assert client.get(f'{BASE}/sections/{SECTION}/registrations').json()['total'] == 1
    assert client.get(f'{BASE}/sections/{SECTION}/batches').json()[0]['batch_id'] == BATCH
    saved = next(row for table, row in db.writes if table == 'student_registrations')
    assert saved['institution_id'] == TENANT and saved['created_by'] == USER
    assert not {'section_id', 'course_id', 'course_offering_id'} & saved.keys()
    assert not {'faculty_section_assignments', 'faculty_responsibilities'} & set(db.reads)
    assert [table for table, _ in db.writes] == ['student_registrations', 'admin_audit_log']


def test_admin_roster_history_pending_filters_and_details_use_the_shared_services(api):
    client, _, _ = api
    assert client.post(f'{BASE}/sections/{SECTION}/registrations', json=PAYLOAD).status_code == 201
    roster = client.get(f'{BASE}/sections/{SECTION}/students?registration=PENDING_APPROVAL').json()
    assert roster['total'] == 1 and roster['items'][0]['student_name'] == 'Ben Rao'
    assert client.get(f'{BASE}/sections/{SECTION}/students?search=missing').json()['total'] == 0
    profile = client.get(f'{BASE}/roster/{ROSTER}/profile').json()
    assert profile['student']['register_number'] == 'CS002' and profile['total'] == 0
    history = client.get(f'{BASE}/sections/{SECTION}/history?search=CS001').json()
    assert history['total'] == 1 and history['items'][0]['action'] == 'class_registered'


def test_roster_batch_filter_uses_saved_class_cohort_before_pagination_and_counts(api):
    client, db, _ = api
    original = db.tables['faculty_attendance_rosters'][0]
    db.tables['faculty_attendance_rosters'].extend([
        {**original, 'roster_id': 'other-roster', 'register_number': 'CS003'},
        {**original, 'roster_id': 'legacy-roster', 'register_number': 'CS004'},
        {**original, 'roster_id': 'conflicting-roll', 'register_number': 'CS005', 'university_roll_number': 'U2'},
        {**original, 'roster_id': 'progressed-student', 'register_number': 'CS006'},
    ])
    assert client.post(f'{BASE}/sections/{SECTION}/registrations', json={**PAYLOAD, 'register_number': 'CS002'}).status_code == 201
    saved = db.tables['student_registrations'][0]
    db.tables['student_registrations'].extend([
        {**saved, 'registration_id': 'other-batch', 'batch_id': USER, 'register_number': 'CS003'},
        {**saved, 'registration_id': 'foreign', 'institution_id': FOREIGN, 'register_number': 'CS004'},
        {**saved, 'registration_id': 'wrong-program', 'program_id': FOREIGN, 'register_number': 'CS004'},
        {**saved, 'registration_id': 'wrong-roll', 'register_number': 'CS005', 'university_roll_number': 'U1'},
        {**saved, 'registration_id': 'older-term', 'semester_id': FOREIGN, 'academic_year_id': FOREIGN, 'section_code': 'B', 'register_number': 'CS006'},
    ])
    path = f'{BASE}/sections/{SECTION}/students?batch_id={BATCH}&registration=PENDING_APPROVAL&limit=1'
    result = client.get(path).json()
    assert result['total'] == 2 and result['items'][0]['register_number'] == 'CS002'
    assert client.get(path + '&offset=1').json()['items'][0]['register_number'] == 'CS006'
    assert client.get(path + '&offset=2').json() == {'items': [], 'total': 2, 'limit': 1, 'offset': 2}
    assert client.get(path + '&search=missing').json()['total'] == 0
    assert client.get(f'{BASE}/sections/{SECTION}/students?batch_id={FOREIGN}').json()['total'] == 0
    assert client.get(f'{BASE}/sections/{SECTION}/students?batch_id=invalid').status_code == 422
    assert client.get(f'{BASE}/sections/{FOREIGN}/students?batch_id={BATCH}').status_code == 403


def test_class_batch_queries_and_archived_batch_options_are_institution_scoped(api):
    client, db, _ = api
    assert client.post(f'{BASE}/sections/{SECTION}/registrations', json=PAYLOAD).status_code == 201
    assert client.get(f'{BASE}/sections/{SECTION}/registrations?batch_id={BATCH}&search=ada').json()['total'] == 1
    assert client.get(f'{BASE}/sections/{SECTION}/registrations?batch_id={FOREIGN}').json()['total'] == 0
    db.tables['academic_batches'][0]['is_active'] = False
    assert client.get(f'{BASE}/sections/{SECTION}/batches').json() == []
    assert client.get(f'{BASE}/sections/{SECTION}/batches?include_inactive=true').json()[0]['batch_id'] == BATCH


@pytest.mark.parametrize('suffix', ['students', 'history', 'registrations', 'batches'])
def test_foreign_or_inactive_sections_never_grant_access(api, suffix):
    client, db, _ = api
    db.reads.clear()
    response = client.get(f'{BASE}/sections/{FOREIGN}/{suffix}')
    assert response.status_code == 403
    assert not db.reads and not db.writes


@pytest.mark.parametrize('role', ['staff', 'faculty', 'student', 'super_admin'])
def test_non_admin_roles_cannot_use_admin_student_workflows_even_with_permissions(api, role):
    client, db, user = api
    user['roles'] = [role]
    user['role_assignments'][0]['role'] = role
    assert client.get(BASE + '/sections').status_code == 403
    assert client.post(f'{BASE}/sections/{SECTION}/registrations', json=PAYLOAD).status_code == 403
    assert not db.writes


def test_create_permission_and_batch_are_rechecked_server_side(api):
    client, db, user = api
    user['effective_permissions'].remove('students.create')
    assert client.get(BASE + '/sections').json()[0]['can_manage'] is False
    assert client.post(f'{BASE}/sections/{SECTION}/registrations', json=PAYLOAD).status_code == 403
    user['effective_permissions'].append('students.create')
    db.tables['academic_batches'][0]['is_active'] = False
    response = client.post(f'{BASE}/sections/{SECTION}/registrations', json=PAYLOAD)
    assert response.status_code == 422 and response.json()['error']['code'] == 'BATCH_UNAVAILABLE'
    assert not db.writes


def test_missing_attendance_permission_and_foreign_profile_fail_closed(api):
    client, _, user = api
    assert client.get(f'{BASE}/roster/{FOREIGN}/profile').status_code == 404
    user['effective_permissions'].remove('attendance.read')
    assert client.get(f'{BASE}/sections/{SECTION}/history').status_code == 403
    assert client.get(f'{BASE}/sections/{SECTION}/students').status_code == 403
