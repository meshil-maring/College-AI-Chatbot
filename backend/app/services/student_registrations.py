"""Class registration without inserting subject roster or attendance records."""

from functools import wraps
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all, read_rows
from app.schemas.student_registrations import StudentRegistrationCreate
from app.services.faculty_attendance import _assert_assigned, _identity_candidates, match_identity
from app.services.faculty_responsibilities import authorize_section

_CLASS_FIELDS = ('program_id', 'academic_year_id', 'semester_id')


def schema_required(operation):
    @wraps(operation)
    def guarded(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except APIError as error:
            if error.code not in {'42P01', 'PGRST205', 'PGRST204', '42703'} or not any(name in error.message for name in ('student_registrations', 'academic_batches')):
                raise
            raise AppError('Class registration is unavailable until the database update is applied. Please contact your administrator.',
                           503, 'STUDENT_REGISTRATION_SCHEMA_UNAVAILABLE') from error
    return guarded


def _status(student):
    if not student:
        return 'UNREGISTERED'
    if student.get('approval_status') != 'approved':
        return 'PENDING_APPROVAL'
    return 'ACTIVE' if student.get('is_active') and student.get('status') == 'active' else 'INACTIVE'


def _project(row, student, errors=()):
    return {**row, 'roster_status': _status(student),
            'linked_student_id': student['student_id'] if student and not errors else None,
            'identity_conflict': bool(errors), 'subjects_assigned': False}


@schema_required
def available_batches(user: dict, scope_section_id: UUID, *, include_inactive: bool = False) -> list[dict]:
    scope = authorize_section(user, scope_section_id, 'students.read')
    query = (get_admin_client().table('academic_batches')
        .select('batch_id, program_id, start_year, end_year, is_active')
        .eq('institution_id', str(user['institution_id'])).eq('program_id', str(scope['program_id'])))
    if not include_inactive:
        query = query.eq('is_active', True)
    return read_all(query.order('start_year', desc=True).order('batch_id'))


@schema_required
def create_registration(user: dict, scope_section_id: UUID, payload: StudentRegistrationCreate, *, permission: str = 'attendance.manage') -> dict:
    # The section is an authorization reference only. Its subject and offering
    # identifiers are deliberately absent from the saved registration.
    scope = _assert_assigned(user, scope_section_id, permission)
    tenant = str(user['institution_id'])
    db = get_admin_client()
    batches = read_rows(db.table('academic_batches').select('batch_id, start_year, end_year')
        .eq('batch_id', str(payload.batch_id)).eq('institution_id', tenant)
        .eq('program_id', str(scope['program_id'])).eq('is_active', True).range(0, 0))
    if not batches:
        raise AppError('The selected batch is unavailable for this branch. Refresh the batch list or ask your administrator to add an active batch in Academic Setup.', 422, 'BATCH_UNAVAILABLE')
    row = payload.model_dump(exclude={'batch_id'})
    row.update(batch_id=str(payload.batch_id), batch_start_year=batches[0]['start_year'], batch_end_year=batches[0]['end_year'])
    if row.get('email'):
        from email_validator import EmailNotValidError, validate_email
        try:
            row['email'] = validate_email(row['email'], check_deliverability=False).normalized
        except EmailNotValidError as error:
            raise AppError('Email format is invalid', 422, 'INVALID_EMAIL') from error
    student, errors = match_identity(tenant, row, _identity_candidates(db, tenant, [row]))
    if student and student.get('program_id') and str(student['program_id']) != str(scope['program_id']):
        errors.append('Student belongs to a different branch')
    if errors:
        raise AppError('; '.join(errors), 422, 'IDENTITY_CONFLICT')
    row.update({key: str(scope[key]) for key in _CLASS_FIELDS})
    row.update(institution_id=tenant, section_code=scope.get('section_code') or scope['code'], created_by=str(user['user_id']))
    try:
        created = read_rows(db.table('student_registrations').insert(row))[0]
    except APIError as error:
        if error.code == '23505':
            raise AppError('A class registration already exists for these student identifiers', 409, 'REGISTRATION_DUPLICATE') from error
        if error.code == '23514':
            raise AppError('The class or batch changed while registering. Refresh the available options and try again.', 409, 'BATCH_UNAVAILABLE') from error
        raise
    return _project(created, student)


def class_rows(db, tenant: str, scope: dict, batch_id: UUID | None = None) -> list[dict]:
    """Saved cohorts in the authorized class; never infer a batch from a year."""
    query = (db.table('student_registrations').select('*').eq('institution_id', tenant)
             .eq('section_code', scope.get('section_code') or scope['code']).order('register_number').order('registration_id'))
    for field in _CLASS_FIELDS:
        query = query.eq(field, str(scope[field]))
    if batch_id:
        query = query.eq('batch_id', str(batch_id))
    return read_all(query)


@schema_required
def list_registrations(user: dict, scope_section_id: UUID, *, limit=100, offset=0, registration=None,
                       batch_id: UUID | None = None, search: str = '', sort: str = 'register_number') -> dict:
    scope = authorize_section(user, scope_section_id, 'students.read')
    tenant = str(user['institution_id'])
    db = get_admin_client()
    rows = class_rows(db, tenant, scope, batch_id)
    term = search.strip().casefold()
    if term:
        rows = [row for row in rows if any(term in str(row.get(key) or '').casefold()
                for key in ('student_name', 'register_number', 'university_roll_number', 'email'))]
    rows.sort(key=lambda row: (str(row.get(sort) or '').casefold(), str(row['registration_id'])))
    page = rows if registration else rows[offset:offset + limit]
    candidates = _identity_candidates(db, tenant, page)
    items = []
    for row in page:
        student, errors = match_identity(tenant, row, candidates)
        if student and student.get('program_id') and str(student['program_id']) != str(row['program_id']):
            student, errors = None, ['Student branch conflicts with registration']
        items.append(_project(row, student, errors))
    if registration:
        items = [row for row in items if row['roster_status'] == registration and not row['identity_conflict']]
        return {'items': items[offset:offset + limit], 'total': len(items)}
    return {'items': items, 'total': len(rows)}
