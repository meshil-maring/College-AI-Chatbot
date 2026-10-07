"""Scope/validity/security regression tests; no live database is used."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.api import faculty
from app.core.errors import AppError
from app.core.security import SUPPORTED_ROLES, get_current_user, has_permission, resolve_primary_role
from app.main import app
from app.schemas.faculty_responsibilities import AssignmentValidity, ResponsibilityCreate
from app.services import faculty_attendance, faculty_responsibilities as service
from app.services.authorization import academic_scope_contains, assignment_is_active, effective_authorization

TENANT = '30000000-0000-0000-0000-000000000001'
OTHER_TENANT = '30000000-0000-0000-0000-000000000002'
USER = '10000000-0000-0000-0000-000000000001'
ADMIN = '10000000-0000-0000-0000-000000000002'
SECTION = '20000000-0000-0000-0000-000000000001'
SIBLING = '20000000-0000-0000-0000-000000000002'
APPOINTMENT = '40000000-0000-0000-0000-000000000001'
NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def principal(role='faculty', user_id=USER, tenant=TENANT):
    return {'user_id': user_id, 'auth_user_id': user_id, 'email': 'faculty@example.test', 'status': 'active',
            'roles': [role], 'institution_id': tenant, 'permissions_resolved': True,
            'effective_permissions': ['profile.own.read', 'faculty.assignments.read', 'students.read', 'attendance.read', 'attendance.manage', 'results.read', 'results.manage'] if role == 'faculty' else ['faculty.assignments.manage'],
            'role_assignments': [{'role': role, 'scope_type': 'institution', 'scope_id': tenant, 'is_active': True}]}


def resource(**changes):
    return {'institution_id': TENANT, 'section_id': SECTION, 'department_id': 'dept-cse', 'program_id': 'btech-cse',
            'academic_year_id': '2026-27', 'semester_id': 'sem5', 'section_code': 'A', 'course_id': 'data-mining',
            'course_offering_id': 'offering-1', 'code': 'A', 'name': 'Section A',
            'course': {'name': 'Data Mining', 'code': 'DM'}, 'program': {'name': 'B.Tech CSE'},
            'semester': {'name': 'Semester 5'}, 'academic_year': {'name': '2026-27'}, **changes}


def assignment(**changes):
    return {'faculty_user_id': USER, 'institution_id': TENANT, 'section_id': SECTION, 'start_at': (NOW - timedelta(days=1)).isoformat(),
            'end_at': (NOW + timedelta(days=1)).isoformat(), 'is_active': True, 'revoked_at': None, **changes}


def responsibility(kind='department', **changes):
    return {**resource(), **assignment(), 'responsibility_id': APPOINTMENT,
            'scope_type': kind, 'scope_id': 'dept-cse' if kind == 'department' else SECTION,
            'permissions': ['academic.department.read' if kind == 'department' else 'academic.class.read',
                            'academic.reports.read', 'attendance.overview.read', 'attendance.read', 'students.read'], **changes}


def decide(permission, *, user=None, target=None, teaching=None, positions=None, **kw):
    return effective_authorization(user or principal(), target or resource(), permission,
                                   teaching=teaching or [], responsibilities=positions or [], now=NOW, **kw)


def test_core_roles_and_existing_permission_resolution_survive():
    assert set(SUPPORTED_ROLES) == {'super_admin', 'admin', 'faculty', 'staff', 'student'}
    assert resolve_primary_role(['faculty', 'student']) == 'faculty'
    assert resolve_primary_role(['hod', 'class_in_charge', 'teacher']) is None
    assert has_permission(principal(), 'attendance.manage')
    assert not has_permission(principal(), 'permissions.manage')


@pytest.mark.parametrize('state,expected', [
    ({}, True), ({'start_at': NOW.isoformat()}, True), ({'end_at': NOW.isoformat()}, False),
    ({'start_at': (NOW + timedelta(seconds=1)).isoformat()}, False),
    ({'end_at': (NOW - timedelta(seconds=1)).isoformat()}, False),
    ({'is_active': False}, False), ({'revoked_at': NOW.isoformat()}, False),
    ({'start_at': 'invalid'}, False), ({'start_at': '2026-10-07T00:00:00'}, False),
    ({'start_at': None, 'assigned_at': (NOW - timedelta(days=1)).isoformat()}, True),
    ({'start_at': None}, False),
])
def test_shared_half_open_validity(state, expected):
    assert assignment_is_active(assignment(**state), NOW) is expected


@pytest.mark.parametrize('permission', ['attendance.manage', 'attendance.read', 'students.read', 'results.manage'])
def test_teaching_permission_requires_exact_subject_section(permission):
    assert decide(permission, teaching=[assignment()])
    assert not decide(permission, teaching=[assignment(section_id=SIBLING)])
    assert not decide(permission, target=resource(section_id=SIBLING, course_id='operating-systems'), teaching=[assignment()])


@pytest.mark.parametrize('kind', ['department', 'section'])
@pytest.mark.parametrize('permission', ['attendance.read', 'students.read', 'attendance.overview.read', 'academic.reports.read'])
def test_responsibilities_enable_scope_visibility(kind, permission):
    assert decide(permission, positions=[responsibility(kind)])
    assert decide(permission, target=resource(section_id=SIBLING, course_id='operating-systems'), positions=[responsibility(kind)])


@pytest.mark.parametrize('kind', ['department', 'section'])
@pytest.mark.parametrize('permission', ['attendance.manage', 'results.manage', 'users.update', 'roles.manage', 'permissions.manage', 'faculty.assignments.manage'])
def test_positions_never_grant_teaching_edits_or_administration(kind, permission):
    assert not decide(permission, positions=[responsibility(kind)])


@pytest.mark.parametrize('field,value', [('institution_id', OTHER_TENANT), ('program_id', 'other-program'), ('semester_id', 'sem6'), ('academic_year_id', '2027-28'), ('section_code', 'B')])
def test_class_scope_rejects_unrelated_or_forged_academic_context(field, value):
    assert not decide('students.read', target=resource(**{field: value}), positions=[responsibility('section')])


@pytest.mark.parametrize('field,value', [('institution_id', OTHER_TENANT), ('department_id', 'other-department')])
def test_hod_scope_rejects_other_department_or_tenant(field, value):
    assert not decide('attendance.read', target=resource(**{field: value}), positions=[responsibility()])


def test_class_monitoring_includes_cross_department_subjects_in_the_same_program_class():
    assert decide('students.read', target=resource(section_id=SIBLING, department_id='math-department', course_id='math'), positions=[responsibility('section')])
    assert not decide('attendance.manage', target=resource(section_id=SIBLING, department_id='math-department', course_id='math'), positions=[responsibility('section')])


@pytest.mark.parametrize('row_changes', [
    {'faculty_user_id': ADMIN}, {'institution_id': OTHER_TENANT}, {'is_active': False}, {'revoked_at': NOW.isoformat()},
    {'start_at': (NOW + timedelta(days=1)).isoformat()}, {'end_at': NOW.isoformat()},
])
@pytest.mark.parametrize('mode', ['teaching', 'hod', 'class'])
def test_forged_revoked_expired_future_assignments_deny(row_changes, mode):
    teaching = [assignment(**row_changes)] if mode == 'teaching' else []
    positions = [] if mode == 'teaching' else [responsibility('department' if mode == 'hod' else 'section', **row_changes)]
    assert not decide('attendance.read', teaching=teaching, positions=positions)


@pytest.mark.parametrize('changes', [{'status': 'inactive'}, {'institution_id': OTHER_TENANT}, {'roles': ['student']}, {'role_assignments': []}, {'user_id': ADMIN}])
def test_account_tenant_identity_and_role_state_are_required(changes):
    assert not decide('students.read', user={**principal(), **changes}, teaching=[assignment()], positions=[responsibility()])


@pytest.mark.parametrize('modes', [('hod', 'class'), ('hod', 'teaching'), ('class', 'teaching'), ('hod', 'class', 'teaching')])
def test_multiple_positions_and_teaching_coexist(modes):
    positions = ([responsibility()] if 'hod' in modes else []) + ([responsibility('section')] if 'class' in modes else [])
    teaching = [assignment()] if 'teaching' in modes else []
    assert decide('students.read', positions=positions, teaching=teaching)
    assert decide('attendance.manage', positions=positions, teaching=teaching) is ('teaching' in modes)
    assert not decide('attendance.manage', target=resource(section_id=SIBLING), positions=positions, teaching=teaching)


def test_revoked_role_permission_is_not_resurrected_by_teaching():
    assert not decide('attendance.manage', user={**principal(), 'effective_permissions': []}, teaching=[assignment()])


def test_ownership_guard_is_independent_of_scope():
    assert decide('attendance.manage', teaching=[assignment()], require_owner=True, owner_user_id=USER)
    assert not decide('attendance.manage', teaching=[assignment()], require_owner=True, owner_user_id=ADMIN)


@pytest.mark.parametrize('kind,fields', [
    ('institution', {}), ('department', {'department_id': 'dept-cse'}),
    ('program', {'program_id': 'btech-cse'}),
    ('semester', {'program_id': 'btech-cse', 'semester_id': 'sem5', 'academic_year_id': '2026-27'}),
    ('course', {'department_id': 'dept-cse', 'course_id': 'data-mining'}),
])
def test_scope_levels_support_future_definition_mappings(kind, fields):
    scope = {'institution_id': TENANT, 'scope_type': kind, **fields}
    assert academic_scope_contains(scope, resource())
    if fields:
        key = next(iter(fields))
        assert not academic_scope_contains({**scope, key: None}, resource())
    assert not academic_scope_contains(scope, resource(institution_id=OTHER_TENANT))


@pytest.mark.parametrize('field,value', [('institution_id', OTHER_TENANT), ('actor_user_id', ADMIN), ('created_by', ADMIN), ('revoked_by', ADMIN), ('permissions', ['*'])])
def test_request_contract_rejects_forged_authorization_fields(field, value):
    with pytest.raises(ValidationError):
        ResponsibilityCreate(**{'faculty_user_id': USER, 'responsibility_code': 'hod', 'scope_type': 'department', 'scope_id': SECTION, 'start_at': NOW.isoformat(), field: value})


@pytest.mark.parametrize('start,end', [(NOW.isoformat(), NOW.isoformat()), (NOW.isoformat(), (NOW - timedelta(days=1)).isoformat()), ('2026-10-07T12:00:00', None)])
def test_invalid_intervals_and_naive_dates_are_rejected(start, end):
    with pytest.raises(ValidationError):
        AssignmentValidity(start_at=start, end_at=end)


@pytest.mark.parametrize('role', ['faculty', 'staff', 'student'])
def test_even_explicit_management_permission_cannot_self_appoint_or_bypass_core_role(role, monkeypatch):
    user = {**principal(role), 'effective_permissions': ['faculty.assignments.manage']}
    db = MagicMock()
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    payload = ResponsibilityCreate(faculty_user_id=USER, responsibility_code='hod', scope_type='department', scope_id=SECTION, start_at=NOW)
    with pytest.raises(AppError) as error:
        service.change_responsibility(user, UUID(TENANT), payload)
    assert error.value.status_code == 403
    db.rpc.assert_not_called()


def test_admin_cannot_self_assign_or_manage_other_tenant(monkeypatch):
    db = MagicMock(); monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    payload = ResponsibilityCreate(faculty_user_id=ADMIN, responsibility_code='hod', scope_type='department', scope_id=SECTION, start_at=NOW)
    with pytest.raises(AppError, match='assign yourself'):
        service.change_responsibility(principal('admin', ADMIN), UUID(TENANT), payload)
    with pytest.raises(AppError, match='scope denied'):
        service.change_responsibility(principal('admin', ADMIN), UUID(OTHER_TENANT), payload)
    db.rpc.assert_not_called()


def test_creation_uses_atomic_rpc_and_server_actor_and_tenant(monkeypatch):
    db = MagicMock(); db.rpc.return_value.execute.return_value.data = APPOINTMENT
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    payload = ResponsibilityCreate(faculty_user_id=USER, responsibility_code='hod', scope_type='department', scope_id=SECTION, start_at=NOW)
    assert service.change_responsibility(principal('admin', ADMIN), UUID(TENANT), payload) == {'responsibility_id': APPOINTMENT}
    name, fields = db.rpc.call_args.args
    assert name == 'manage_faculty_responsibility'
    assert fields['p_actor_user_id'] == ADMIN and fields['p_institution_id'] == TENANT and fields['p_faculty_user_id'] == USER
    assert fields['p_revoke'] is False


@pytest.mark.parametrize('code,http,app_code', [('23P01', 409, 'ASSIGNMENT_CONFLICT'), ('23514', 422, 'INVALID_ASSIGNMENT'), ('23503', 422, 'INVALID_ASSIGNMENT'), ('42501', 403, 'FORBIDDEN'), ('P0002', 404, 'ASSIGNMENT_NOT_FOUND')])
def test_database_domain_errors_are_safe_and_do_not_report_success(code, http, app_code, monkeypatch):
    db = MagicMock(); db.rpc.return_value.execute.side_effect = APIError({'code': code, 'message': 'internal database detail', 'details': None, 'hint': None})
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as error:
        service._rpc('manage_faculty_responsibility', {})
    assert (error.value.status_code, error.value.code) == (http, app_code)
    assert 'internal database detail' not in error.value.message


def test_attendance_write_guard_uses_central_teaching_only_resolution(monkeypatch):
    authorize = MagicMock(return_value=resource()); monkeypatch.setattr(service, 'authorize_section', authorize)
    faculty_attendance._assert_assigned(principal(), UUID(SECTION))
    authorize.assert_called_once_with(principal(), UUID(SECTION), 'attendance.manage', teaching_only=True)


def test_attendance_roster_read_uses_responsibility_aware_resolution(monkeypatch):
    authorize = MagicMock(return_value=resource()); monkeypatch.setattr(service, 'authorize_section', authorize)
    db = MagicMock(); db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
    monkeypatch.setattr(faculty_attendance, 'get_admin_client', lambda: db)
    assert faculty_attendance.list_roster(principal(), UUID(SECTION)) == []
    authorize.assert_called_once_with(principal(), UUID(SECTION), 'attendance.read')


def test_forged_section_is_denied_before_assignments_query(monkeypatch):
    monkeypatch.setattr(service, '_active_sections', lambda _tenant: [resource()])
    db = MagicMock(); monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as error:
        service.authorize_section(principal(), UUID(SIBLING), 'attendance.manage')
    assert error.value.code == 'FACULTY_SCOPE_DENIED'
    db.table.assert_not_called()


@pytest.mark.parametrize('state,expected', [({}, True), ({'end_at': '2000-01-01T00:00:00Z'}, False), ({'revoked_at': NOW.isoformat()}, False), ({'is_active': False}, False)])
def test_real_section_resolver_checks_live_teaching_validity(state, expected, monkeypatch):
    row = assignment(start_at='2000-01-01T00:00:00Z', end_at=None, **state) if 'end_at' not in state else assignment(start_at='1999-01-01T00:00:00Z', **state)
    monkeypatch.setattr(service, '_active_sections', lambda _tenant: [resource()])
    monkeypatch.setattr(service, '_all_rows', lambda _query: [row])
    monkeypatch.setattr(service, 'get_admin_client', MagicMock())
    if expected:
        assert service.authorize_section(principal(), UUID(SECTION), 'attendance.manage', teaching_only=True)['section_id'] == SECTION
    else:
        with pytest.raises(AppError):
            service.authorize_section(principal(), UUID(SECTION), 'attendance.manage', teaching_only=True)


@pytest.mark.parametrize('path,method,body', [
    ('/api/v1/admin/faculty-responsibilities', 'post', {'faculty_user_id': USER, 'responsibility_code': 'hod', 'scope_type': 'department', 'scope_id': SECTION, 'start_at': NOW.isoformat()}),
    ('/api/v1/admin/faculty-responsibilities', 'get', None),
    (f'/api/v1/admin/faculty-responsibilities/{APPOINTMENT}', 'delete', None),
])
def test_faculty_with_positions_is_still_denied_admin_routes(path, method, body):
    app.dependency_overrides[get_current_user] = lambda: principal()
    try:
        response = getattr(TestClient(app), method)(path, **({'json': body} if body else {}))
    finally: app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403


def test_forged_or_revoked_responsibility_report_denies(monkeypatch):
    monkeypatch.setattr(service, 'faculty_context', lambda _user: {'responsibilities': [], 'teaching_assignments': []})
    app.dependency_overrides[faculty._FACULTY] = lambda: principal()
    try: response = TestClient(app).get(f'/api/v1/faculty/responsibilities/{APPOINTMENT}/report')
    finally: app.dependency_overrides.pop(faculty._FACULTY, None)
    assert response.status_code == 403


def test_auth_me_adds_faculty_context_without_widening_existing_permissions(monkeypatch):
    import app.services.authorization as authz
    expected = {'responsibilities': [], 'teaching_assignments': [], 'responsibility_permissions': []}
    monkeypatch.setattr(authz, 'resolve_institution_authorization_context', lambda *_args, **_kw: SimpleNamespace(institution_id=UUID(TENANT)))
    monkeypatch.setattr(service, 'faculty_context', lambda _user: expected)
    app.dependency_overrides[get_current_user] = lambda: principal()
    try: response = TestClient(app).get('/api/v1/auth/me')
    finally: app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200
    assert response.json()['faculty_context'] == expected
    assert response.json()['effective_permissions'] == principal()['effective_permissions']


def test_faculty_login_succeeds_when_responsibility_table_is_missing(monkeypatch, caplog):
    import app.services.authorization as authz

    db = MagicMock()
    query = db.table.return_value
    for method in ('select', 'eq', 'order', 'range'):
        getattr(query, method).return_value = query
    query.execute.side_effect = APIError({
        'code': 'PGRST205',
        'message': "Could not find the table 'public.responsibility_definitions' in the schema cache",
        'details': None, 'hint': None,
    })
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    monkeypatch.setattr(authz, 'resolve_institution_authorization_context', lambda *_args, **_kw: SimpleNamespace(institution_id=UUID(TENANT)))
    app.dependency_overrides[get_current_user] = lambda: principal()
    try:
        response = TestClient(app).get('/api/v1/auth/me')
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['authenticated'] is True
    assert payload['role'] == 'faculty'
    assert payload['institution_id'] == TENANT
    assert payload['effective_permissions'] == principal()['effective_permissions']
    assert payload['faculty_context'] == {
        'responsibilities': [], 'teaching_assignments': [], 'responsibility_permissions': [],
    }
    assert 'faculty_schema_unavailable' in caplog.text
    assert '20261011000000_faculty_responsibilities_and_validity.sql' in caplog.text


@pytest.mark.parametrize('component,code,message', [
    ('list_responsibilities', 'PGRST205', "Could not find the table 'public.faculty_responsibilities' in the schema cache"),
    ('list_responsibilities', '42P01', 'relation "public.responsibility_definitions" does not exist'),
    ('list_responsibilities', 'PGRST200', "Could not find a relationship between 'responsibility_definitions' and 'responsibility_permissions' in the schema cache"),
    ('list_own_faculty_assignments', 'PGRST205', "Could not find the table 'public.faculty_section_assignments' in the schema cache"),
    ('list_own_faculty_assignments', '42703', 'column faculty_section_assignments.start_at does not exist'),
    ('list_own_faculty_assignments', 'PGRST204', "Could not find the 'start_at' column of 'faculty_section_assignments' in the schema cache"),
])
def test_missing_faculty_schema_returns_service_unavailable(component, code, message, monkeypatch):
    monkeypatch.setattr(service, 'list_responsibilities', MagicMock(return_value=[]))
    monkeypatch.setattr(service, 'list_own_faculty_assignments', MagicMock(return_value=[]))
    getattr(service, component).side_effect = APIError({'code': code, 'message': message, 'details': None, 'hint': None})
    app.dependency_overrides[faculty._FACULTY] = lambda: principal()
    try:
        response = TestClient(app).get('/api/v1/faculty/context')
    finally:
        app.dependency_overrides.pop(faculty._FACULTY, None)
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'FACULTY_SCHEMA_UNAVAILABLE'
    assert message not in response.text


@pytest.mark.parametrize('code,message', [
    ('PGRST205', "Could not find the table 'public.departments' in the schema cache"),
    ('42501', 'permission denied for table responsibility_definitions'),
    ('PGRST000', 'connection failed while querying responsibility_definitions'),
])
def test_unrelated_database_failures_are_not_treated_as_missing_faculty_schema(code, message, monkeypatch):
    error = APIError({'code': code, 'message': message, 'details': None, 'hint': None})
    monkeypatch.setattr(service, 'list_responsibilities', MagicMock(side_effect=error))
    with pytest.raises(APIError) as caught:
        service.faculty_context(principal())
    assert caught.value is error


@pytest.mark.parametrize('source', ['institution', 'faculty'])
def test_login_schema_fallback_does_not_bypass_authorization_denial(source, monkeypatch):
    import app.services.authorization as authz

    resolver = MagicMock(return_value=SimpleNamespace(institution_id=UUID(TENANT)))
    context = MagicMock(return_value={})
    denied = AppError('Faculty institution grant required', 403, 'FORBIDDEN')
    (resolver if source == 'institution' else context).side_effect = denied
    monkeypatch.setattr(authz, 'resolve_institution_authorization_context', resolver)
    monkeypatch.setattr(service, 'faculty_context', context)
    app.dependency_overrides[get_current_user] = lambda: principal()
    try:
        response = TestClient(app).get('/api/v1/auth/me')
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'FORBIDDEN'
    if source == 'institution':
        context.assert_not_called()


def test_scope_revalidation_removes_changed_or_inactive_class_anchor():
    row = responsibility('section')
    options = {'departments': [], 'sections': [resource()]}
    assert service._live_scope(row, options)
    assert service._live_scope(row, {'departments': [], 'sections': []}) is None
    assert service._live_scope(row, {'departments': [], 'sections': [resource(program_id='other-program')]}) is None


class MemoryQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.bounds = None

    def select(self, _columns): return self
    def order(self, _column, **_kwargs): return self
    def eq(self, column, value):
        def matches(row):
            current = row
            for key in column.split('.'):
                current = current.get(key) if isinstance(current, dict) else None
            return str(current) == str(value)
        self.filters.append(matches)
        return self
    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self
    def range(self, start, end): self.bounds = (start, end); return self
    def execute(self):
        rows = [row for row in self.rows if all(test(row) for test in self.filters)]
        if self.bounds: rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


def test_complete_report_excludes_other_scopes_and_summarizes_recorded_attendance(monkeypatch):
    position = responsibility(start_at='2000-01-01T00:00:00Z', end_at=None, permissions=['academic.department.read', 'academic.reports.read', 'students.read', 'attendance.overview.read', 'faculty.read'])
    monkeypatch.setattr(service, 'faculty_context', lambda _user: {'responsibilities': [position]})
    monkeypatch.setattr(service, '_active_sections', lambda _tenant: [resource(), resource(section_id=SIBLING), resource(section_id='other-section', department_id='other-department')])
    tables = {
        'faculty_attendance_rosters': [
            {'roster_id': 'r1', 'section_id': SECTION, 'institution_id': TENANT, 'student_name': 'Student One'},
            {'roster_id': 'r2', 'section_id': SIBLING, 'institution_id': TENANT, 'student_name': 'Student Two'},
            {'roster_id': 'secret', 'section_id': 'other-section', 'institution_id': TENANT, 'student_name': 'Outside Department'},
            {'roster_id': 'foreign', 'section_id': SECTION, 'institution_id': OTHER_TENANT, 'student_name': 'Other Institution'},
        ],
        'faculty_attendance_sessions': [{'session_id': f's{i}', 'institution_id': TENANT, 'section_id': SECTION} for i in range(3)] + [{'session_id': 's-secret', 'institution_id': TENANT, 'section_id': 'other-section'}],
        'faculty_attendance_records': [
            {'record_id': 'p', 'session_id': 's0', 'roster_id': 'r1', 'status': 'present'},
            {'record_id': 'l', 'session_id': 's1', 'roster_id': 'r1', 'status': 'late'},
            {'record_id': 'a', 'session_id': 's2', 'roster_id': 'r1', 'status': 'absent'},
            {'record_id': 'x', 'session_id': 's-secret', 'roster_id': 'secret', 'status': 'present'},
        ],
        'faculty_section_assignments': [assignment(start_at='2000-01-01T00:00:00Z', end_at=None), assignment(faculty_user_id=ADMIN, start_at='2000-01-01T00:00:00Z', end_at=None)],
        'user_roles': [{'user_id': USER, 'scope_type': 'institution', 'scope_id': TENANT, 'roles': {'name': 'faculty', 'is_active': True}}, {'user_id': ADMIN, 'scope_type': 'institution', 'scope_id': TENANT, 'roles': {'name': 'staff', 'is_active': True}}],
        'users': [{'id': USER, 'first_name': 'Ada', 'last_name': 'Lovelace', 'status': 'active'}, {'id': ADMIN, 'first_name': 'Staff', 'last_name': 'Member', 'status': 'active'}],
    }
    monkeypatch.setattr(service, 'get_admin_client', lambda: SimpleNamespace(table=lambda name: MemoryQuery(tables[name])))
    report = service.responsibility_report(principal(), UUID(APPOINTMENT))
    assert report['session_count'] == 3 and len(report['sections']) == 2
    assert {s['roster_id'] for s in report['students']} == {'r1', 'r2'}
    assert report['students'][0]['attendance_percentage'] == 33.33
    assert report['students'][1]['attendance_percentage'] is None
    assert [s['roster_id'] for s in report['low_attendance']] == ['r1']
    assert [f['id'] for f in report['faculty']] == [USER]


def test_class_report_does_not_disclose_faculty_without_explicit_permission(monkeypatch):
    position = responsibility('section', start_at='2000-01-01T00:00:00Z', end_at=None)
    monkeypatch.setattr(service, 'faculty_context', lambda _user: {'responsibilities': [position]})
    monkeypatch.setattr(service, '_active_sections', lambda _tenant: [resource()])
    tables_read = []
    def table(name): tables_read.append(name); return MemoryQuery([])
    monkeypatch.setattr(service, 'get_admin_client', lambda: SimpleNamespace(table=table))
    assert service.responsibility_report(principal(), UUID(APPOINTMENT))['faculty'] == []
    assert 'users' not in tables_read and 'faculty_section_assignments' not in tables_read


def test_removing_mapped_permission_immediately_denies_report(monkeypatch):
    position = responsibility('section', permissions=['academic.class.read'])
    monkeypatch.setattr(service, 'faculty_context', lambda _user: {'responsibilities': [position]})
    db = MagicMock(); monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as error:
        service.responsibility_report(principal(), UUID(APPOINTMENT))
    assert error.value.code == 'FORBIDDEN'
    db.table.assert_not_called()


def test_report_query_pagination_preserves_rows_beyond_rest_limit():
    from app.repositories.query_pages import read_all, read_one
    rows = [{'id': index} for index in range(1201)]
    assert read_all(MemoryQuery(rows)) == rows
    with pytest.raises(AppError, match='projection'):
        read_one(SimpleNamespace(execute=lambda: SimpleNamespace(data=['not-an-object'])))


def test_migration_preserves_teaching_ids_and_contains_database_conflict_and_audit_guards():
    from pathlib import Path
    migration = (Path(__file__).resolve().parents[2] / 'supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql').read_text(encoding='utf-8')
    assert 'UPDATE public.faculty_section_assignments SET start_at = assigned_at' in migration
    assert 'DROP TABLE' not in migration and 'DELETE FROM public.faculty_section_assignments' not in migration
    assert 'EXCLUDE USING gist' in migration and "tstzrange(start_at, end_at, '[)')" in migration
    assert 'exclusive_scope' in migration and 'p_actor_user_id = p_faculty_user_id' in migration
    assert "'faculty.responsibility.revoke'" in migration and "'faculty.responsibility.update'" in migration
    assert "'faculty.assignment.update'" in migration and 'ENABLE ROW LEVEL SECURITY' in migration
    assert 'REVOKE INSERT, UPDATE, DELETE' in migration
