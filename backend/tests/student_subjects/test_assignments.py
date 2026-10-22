from uuid import UUID

import pytest
from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.services.students import subject_assignments as service
from .support import Database, OTHER, REGISTRATION, SECTION, SCOPE, TENANT, principal, registration


@pytest.fixture
def database(monkeypatch):
    db = Database()
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    monkeypatch.setattr(service, 'authorize_section', lambda *_args, **_kwargs: SCOPE)
    return db


def assign():
    return service.assign_student(principal(), UUID(SECTION), UUID(REGISTRATION))


def test_assignment_creates_only_the_target_subject_membership_and_is_idempotent(database):
    result = assign()
    assert result['status'] == 'assigned'
    table, row = database.writes[0]
    assert table == 'faculty_attendance_rosters'
    assert row['section_id'] == SECTION and row['institution_id'] == TENANT
    assert row['course_offering_id'] == SCOPE['course_offering_id']
    assert row['roster_status'] == 'UNREGISTERED' and row['linked_student_id'] is None
    assert database.tables['student_registrations'] == [registration()]
    assert assign()['status'] == 'already_assigned' and len(database.writes) == 1
    assert service.unassigned_students(principal(), UUID(SECTION)) == {'items': [], 'total': 0}


@pytest.mark.parametrize('changes', [
    {'institution_id': OTHER}, {'program_id': OTHER}, {'semester_id': OTHER},
    {'academic_year_id': OTHER}, {'section_code': 'B'}, {'registration_id': OTHER},
])
def test_assignment_rejects_foreign_class_or_registration(database, changes):
    database.tables['student_registrations'][0].update(changes)
    with pytest.raises(AppError) as error:
        assign()
    assert error.value.code == 'REGISTRATION_NOT_FOUND'
    assert not database.writes


def test_read_and_mutation_recheck_scope_before_database_access(database, monkeypatch):
    def denied(*_args, **_kwargs):
        raise AppError('Expired assignment', 403, 'FACULTY_SCOPE_DENIED')
    monkeypatch.setattr(service, 'authorize_section', denied)
    with pytest.raises(AppError): assign()
    with pytest.raises(AppError): service.unassigned_students(principal(), UUID(SECTION))
    assert not database.reads and not database.writes


def test_listing_excludes_only_the_selected_subject_and_filters_before_pagination(database):
    database.tables['student_registrations'] += [registration(registration_id=OTHER, register_number='CS002', student_name='Ben')]
    database.tables['faculty_attendance_rosters'] = [{'roster_id': 'other-subject', 'institution_id': TENANT,
        'section_id': OTHER, 'register_number': 'CS001'}]
    assert service.unassigned_students(principal(), UUID(SECTION))['total'] == 2
    assign()
    result = service.unassigned_students(principal(), UUID(SECTION), search='Ben', batch_id='batch', limit=1)
    assert result['total'] == 1 and result['items'][0]['register_number'] == 'CS002'
    assert service.unassigned_students(principal(), UUID(SECTION), batch_id=OTHER)['total'] == 0
    assert service.unassigned_students(principal(), UUID(SECTION), offset=1)['items'] == []


@pytest.mark.parametrize('approval,active,status,linked', [
    ('pending', False, 'PENDING_APPROVAL', None), ('approved', True, 'ACTIVE', 'student'),
    ('approved', False, 'INACTIVE', 'student'),
])
def test_assignment_preserves_account_approval_and_activation(database, approval, active, status, linked):
    account = {'student_id': 'student', 'institution_id': TENANT, 'register_number': 'CS001',
               'approval_status': approval, 'is_active': active, 'status': 'active' if active else 'inactive',
               'program_id': 'program', 'academic_year_id': 'year'}
    database.tables['students'] = [account.copy()]
    assign()
    row = database.writes[0][1]
    assert row['roster_status'] == status and row['linked_student_id'] == linked
    assert database.tables['students'] == [account]


@pytest.mark.parametrize('changes', [{'program_id': OTHER}, {'academic_year_id': OTHER}, {'university_roll_number': 'U2'}])
def test_identity_conflicts_are_visible_and_never_assigned(database, changes):
    database.tables['student_registrations'][0]['university_roll_number'] = 'U1'
    database.tables['students'] = [{'student_id': 'student', 'institution_id': TENANT,
                                  'register_number': 'CS001', **changes}]
    item = service.unassigned_students(principal(), UUID(SECTION))['items'][0]
    assert item['assignment_errors']
    with pytest.raises(AppError) as error:
        assign()
    assert error.value.code == 'IDENTITY_CONFLICT' and not database.writes


def test_conflicting_roster_identifiers_are_not_silently_treated_as_assigned(database):
    database.tables['student_registrations'][0]['university_roll_number'] = 'U1'
    database.tables['faculty_attendance_rosters'] = [{'roster_id': 'conflict', 'institution_id': TENANT,
        'section_id': SECTION, 'register_number': 'OTHER', 'university_roll_number': 'U1'}]
    assert service.unassigned_students(principal(), UUID(SECTION))['items'][0]['assignment_errors']
    with pytest.raises(AppError): assign()
    assert not database.writes


def test_roll_number_is_required_after_first_semester(database):
    database.tables['semesters'][0]['semester_number'] = 2
    assert service.unassigned_students(principal(), UUID(SECTION))['items'][0]['assignment_errors']
    with pytest.raises(AppError) as error:
        assign()
    assert error.value.code == 'MISSING_REQUIRED_FIELD' and not database.writes


def test_concurrent_duplicate_is_a_safe_conflict(database):
    database.error = APIError({'code': '23505', 'message': 'private constraint', 'details': '', 'hint': ''})
    with pytest.raises(AppError) as error:
        assign()
    assert error.value.status_code == 409 and 'private' not in error.value.message
