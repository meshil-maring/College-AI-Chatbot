"""Assign saved class registrations to an authorized subject roster."""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.students import subject_assignments as repository
from app.services.faculty.faculty_attendance import _identity_candidates, match_identity
from app.services.faculty.faculty_responsibilities import authorize_section
from app.services.students.student_registrations import _project, class_rows, schema_required
from app.services.academics import legacy_rosters


def _identity(tenant, scope, row, candidates):
    student, errors = match_identity(tenant, row, candidates)
    if student and any(student.get(field) and str(student[field]) != str(scope[field])
                       for field in ('program_id', 'academic_year_id')):
        errors.append('Student belongs to a different branch or academic year')
    return student, errors


def _membership(row, student, roster):
    matches = [item for item in roster if item['register_number'] == row['register_number'] or
               (row.get('university_roll_number') and item.get('university_roll_number') == row['university_roll_number'])]
    if not matches:
        return None, []
    if len(matches) > 1 or any(
        item['register_number'] != row['register_number'] or
        (row.get('university_roll_number') and item.get('university_roll_number') and
         item['university_roll_number'] != row['university_roll_number']) or
        item.get('reconciliation_state') == 'CONFLICT' or
        (item.get('linked_student_id') and (not student or str(item['linked_student_id']) != str(student['student_id'])))
        for item in matches
    ):
        return None, ['Existing subject membership has conflicting identifiers; ask an administrator to review it.']
    return matches[0], []


@schema_required
def unassigned_students(user: dict, section_id: UUID, *, batch_id: UUID | None = None,
                        search: str = '', limit: int = 25, offset: int = 0) -> dict:
    scope = authorize_section(user, section_id, 'students.read')
    db, tenant = get_admin_client(), str(user['institution_id'])
    roster = repository.roster(db, tenant, str(section_id))
    rows = class_rows(db, tenant, scope, batch_id)
    candidates = _identity_candidates(db, tenant, rows)
    semester = repository.semester_number(db, str(scope['semester_id']))
    items = []
    term = search.strip().casefold()
    for row in rows:
        if term and not any(term in str(row.get(key) or '').casefold()
                            for key in ('student_name', 'register_number', 'university_roll_number', 'email')):
            continue
        student, errors = _identity(tenant, scope, row, candidates)
        member, conflicts = _membership(row, student, roster)
        if member and not errors:
            continue
        errors.extend(conflicts)
        if semester != 1 and not row.get('university_roll_number'):
            errors.append('University roll number is required after the first semester.')
        items.append({**_project(row, student, errors), 'assignment_errors': errors})
    return {'items': items[offset:offset + limit], 'total': len(items)}


@schema_required
def assign_student(user: dict, section_id: UUID, registration_id: UUID, *, permission='attendance.manage') -> dict:
    scope = authorize_section(user, section_id, permission, teaching_only=True)
    db, tenant = get_admin_client(), str(user['institution_id'])
    row = repository.registration(db, tenant, scope, str(registration_id))
    if row is None:
        raise AppError('Student registration is unavailable in this class.', 404, 'REGISTRATION_NOT_FOUND')
    student, errors = _identity(tenant, scope, row, _identity_candidates(db, tenant, [row]))
    member, conflicts = _membership(row, student, repository.roster(db, tenant, str(section_id)))
    errors.extend(conflicts)
    if errors:
        raise AppError('; '.join(errors), 422, 'IDENTITY_CONFLICT')
    if member:
        return {'registration_id': str(registration_id), 'roster_id': member['roster_id'], 'status': 'already_assigned'}
    if repository.semester_number(db, str(scope['semester_id'])) != 1 and not row.get('university_roll_number'):
        raise AppError('University roll number is required after the first semester.', 422, 'MISSING_REQUIRED_FIELD')
    return legacy_rosters.assign_subject(db, user, section_id, registration_id, permission)
