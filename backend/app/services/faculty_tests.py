"""Faculty assessments over existing results, rosters, authorization and staging."""

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all, read_one
from app.schemas.faculty_tests import MarkInput
from app.services.authorization import effective_authorization
from app.services.faculty_attendance import (
    MAX_IMPORT_ROWS,
    _identity_candidates,
    match_identity,
    parse_attendance_file,
    validate_import_filename,
)
from app.services.faculty_responsibilities import authorize_section, faculty_context
from app.services.phase81_rbac import _active_sections

ALLOWED_IMPORT_COLUMNS = {'register_number', 'university_roll_number', 'scored_marks', 'mark_status', 'remarks'}


def rpc(user, name, fields):
    try:
        return get_admin_client().rpc(name, {
            **fields, 'p_actor': str(user['user_id']), 'p_tenant': str(user['institution_id'])
        }).execute().data
    except APIError as exc:
        status, code, message = {
            '42501': (403, 'FACULTY_SCOPE_DENIED', 'Teaching, owner or roster authority denied'),
            'P0002': (404, 'TEST_NOT_FOUND', 'Assessment resource not found'),
            '40001': (409, 'TEST_CHANGED', 'The assessment or import changed. Reload and review again.'),
            '23505': (409, 'TEST_CONFLICT', 'A duplicate or overlapping assessment exists'),
            '23514': (422, 'INVALID_TEST_OPERATION', 'Invalid marks, academic date, review or lifecycle state'),
            '23503': (422, 'INVALID_TEST_CONTEXT', 'Invalid academic or roster relationship'),
            '22P02': (422, 'INVALID_TEST_DATA', 'Invalid assessment data'),
        }.get(exc.code, (500, 'TEST_WRITE_FAILED', 'Assessment write failed'))
        raise AppError(message, status, code) from exc


def resources(user):
    context = faculty_context(user)
    return [{**section, 'can_manage': effective_authorization(user, section, 'results.manage',
             teaching=context['teaching_assignments'], responsibilities=[])}
            for section in _active_sections(UUID(str(user['institution_id'])))
            if effective_authorization(user, section, 'results.read', teaching=context['teaching_assignments'],
                                       responsibilities=context['responsibilities'])]


def types(user):
    faculty_context(user)
    return read_all(get_admin_client().table('test_types').select('code,name').eq('is_active', True).order('name'))


def test_row(user, test_id, *, manage=False):
    faculty_context(user)
    row = read_one(get_admin_client().table('faculty_tests').select('*').eq('test_id', str(test_id))
                   .eq('institution_id', str(user['institution_id'])).maybe_single())
    if not row:
        raise AppError('Assessment not found', 404, 'TEST_NOT_FOUND')
    section = authorize_section(user, UUID(row['section_id']), 'results.manage' if manage else 'results.read',
                                teaching_only=manage, owner_user_id=row['created_by'], require_owner=manage)
    row['section'] = section
    row['can_manage'] = str(row['created_by']) == str(user['user_id']) and any(
        s['section_id'] == row['section_id'] and s['can_manage'] for s in resources(user))
    return row


def list_tests(user, section_id, *, offset=0, limit=50):
    faculty_context(user)
    authorize_section(user, section_id, 'results.read')
    rows = read_all(get_admin_client().table('faculty_tests').select('*').eq('institution_id', str(user['institution_id']))
                    .eq('section_id', str(section_id)).order('created_at', desc=True).order('test_id'))
    counts = Counter(row['status'] for row in rows)
    overview = {state.lower(): counts[state] for state in ('DRAFT', 'COMPLETED', 'PUBLISHED', 'LOCKED')}
    overview['upcoming'] = sum(row['status'] == 'SCHEDULED' and row['scheduled_date'] >= datetime.now(UTC).date().isoformat() for row in rows)
    overview['pending_marks'] = sum(row['status'] == 'COMPLETED' and row['marks_state'] == 'DRAFT' for row in rows)
    return {'items': rows[offset:offset + limit], 'total': len(rows), 'overview': overview}


def marks(user, test_id):
    t = test_row(user, test_id)
    roster = read_all(get_admin_client().table('faculty_attendance_rosters').select(
        'roster_id,register_number,university_roll_number,student_name,roster_status,reconciliation_state,linked_student_id')
        .eq('institution_id', str(user['institution_id'])).eq('section_id', t['section_id']).order('register_number').order('roster_id'))
    candidates = _identity_candidates(get_admin_client(), str(user['institution_id']), roster)
    for r in roster:
        identity, errors = match_identity(str(user['institution_id']), r, candidates)
        if errors or (identity and any(identity.get(key) is not None and str(identity[key]) != str(t['section'][key])
                                     for key in ('program_id', 'academic_year_id'))) or (
            r.get('linked_student_id') and str(r['linked_student_id']) != str((identity or {}).get('student_id'))
        ):
            r['reconciliation_state'] = 'CONFLICT'
        r.pop('linked_student_id', None)
    saved = read_all(get_admin_client().table('test_results').select('roster_id,scored_marks,mark_status,remarks,percentage')
                    .eq('institution_id', str(user['institution_id'])).eq('test_id', str(test_id)).order('test_result_id'))
    by_id = {row['roster_id']: row for row in saved}
    t['can_edit_metadata'] = t['can_manage'] and t['status'] in ('DRAFT', 'SCHEDULED') and not saved
    rows = [{**r, **by_id.get(r['roster_id'], {'scored_marks': None, 'mark_status': 'missing', 'remarks': None, 'percentage': None})}
            for r in roster if r['roster_status'] != 'INACTIVE' or r['roster_id'] in by_id]
    for row in rows:
        row['outcome'] = ('pass' if Decimal(str(row['scored_marks'])) >= Decimal(str(t['passing_marks'])) else 'fail') \
            if row['mark_status'] == 'present' and t['passing_marks'] is not None else None
    return {'test': t, 'rows': rows, 'review': calculate_review(rows)}


def calculate_review(rows):
    counts = Counter(r['mark_status'] for r in rows)
    percentages = [Decimal(str(r['percentage'])) for r in rows if r.get('percentage') is not None and r['mark_status'] == 'present']
    return {'total': len(rows), 'entered': len(rows) - counts['missing'], 'missing': counts['missing'],
            'absent': counts['absent'], 'exempt': counts['exempt'], 'not_attempted': counts['not_attempted'],
            'conflicts': sum(r.get('reconciliation_state') == 'CONFLICT' for r in rows),
            'pass': sum(r.get('outcome') == 'pass' for r in rows), 'fail': sum(r.get('outcome') == 'fail' for r in rows),
            'average_percentage': float(sum(percentages) / len(percentages)) if percentages else None}


def save_test(user, section_id, payload, test_id=None):
    faculty_context(user)
    authorize_section(user, section_id, 'results.manage', teaching_only=True)
    if test_id:
        test_row(user, test_id, manage=True)
    fields = payload.model_dump(mode='json')
    version = fields.pop('expected_version', None)
    return rpc(user, 'save_faculty_test', {'p_section': str(section_id), 'p_data': fields,
                                          'p_test': str(test_id) if test_id else None, 'p_version': version})


def save_marks(user, test_id, payload, *, correction=False):
    t = test_row(user, test_id, manage=True)
    if any(row.scored_marks is not None and row.scored_marks > Decimal(str(t['max_marks'])) for row in payload.rows):
        raise AppError('Marks exceed the test maximum', 422, 'INVALID_MARKS')
    return rpc(user, 'save_faculty_test_marks', {'p_test': str(test_id), 'p_version': payload.expected_version,
              'p_rows': [r.model_dump(mode='json') for r in payload.rows], 'p_reason': payload.reason if correction else None})


def transition(user, test_id, payload):
    test_row(user, test_id, manage=True)
    return rpc(user, 'transition_faculty_test', {'p_test': str(test_id), 'p_version': payload.expected_version, 'p_action': payload.action})


def validate_import(rows, roster, maximum):
    if not rows or len(rows) > MAX_IMPORT_ROWS:
        raise AppError('Provide 1–500 rows', 422, 'INVALID_IMPORT_ROWS')
    headers = set(getattr(rows, 'headers', ())) or set().union(*(r.keys() for r in rows))
    if not {'register_number', 'mark_status'}.issubset(headers) or headers - ALLOWED_IMPORT_COLUMNS:
        raise AppError('Use register_number, mark_status, scored_marks and optional university_roll_number/remarks', 422, 'INVALID_IMPORT_COLUMNS')
    by_register = {r['register_number']: r for r in roster}
    seen = set()
    reviewed = []
    for number, raw in enumerate(rows, 2):
        data = {k: v.strip() for k, v in raw.items()}
        errors, warnings = [], []
        identity = data.get('register_number', '')
        r = by_register.get(identity)
        state = 'VALID'
        if not identity or r is None:
            errors.append('Unknown register number in this section'); state = 'ERROR'
        elif r.get('reconciliation_state') == 'CONFLICT' or (data.get('university_roll_number') and data['university_roll_number'] != r.get('university_roll_number')):
            errors.append('Conflicting identifiers'); state = 'CONFLICT'
        elif r['roster_status'] == 'INACTIVE':
            errors.append('Inactive roster'); state = 'ERROR'
        elif r['roster_status'] != 'ACTIVE':
            warnings.append('Marks remain on the existing roster until safe approved registration')
        if identity in seen:
            errors.append('Duplicate student identity'); state = 'DUPLICATE'
        seen.add(identity)
        try:
            value = data.get('scored_marks', '')
            if value and (not value.replace('.', '', 1).isdigit()):
                raise ValueError('Malformed numeric score')
            mark = MarkInput(roster_id=r['roster_id'] if r else UUID(int=0), mark_status=data.get('mark_status', ''),
                             scored_marks=Decimal(value) if value else None, remarks=data.get('remarks'))
            if mark.scored_marks is not None and mark.scored_marks > Decimal(str(maximum)):
                raise ValueError('Marks exceed maximum')
            if mark.mark_status == 'missing':
                errors.append('Missing marks cannot be imported; enter an explicit status')
        except (ValueError, InvalidOperation):
            errors.append('Invalid numeric marks/status: present requires a score within the maximum with at most two decimals; other statuses require empty marks')
        if any(v.lstrip().startswith(('=', '+', '@')) for v in data.values()):
            errors.append('Spreadsheet formulas are not supported')
        if errors and state == 'VALID':
            state = 'ERROR'
        reviewed.append({'row_number': number, 'raw_data': raw, 'normalized_data': data,
                         'validation_status': state, 'errors': errors, 'warnings': warnings})
    summary = Counter(r['validation_status'].lower() for r in reviewed)
    return {'total_rows': len(rows), 'valid': summary['valid'], 'errors': summary['error'],
            'conflicts': summary['conflict'], 'duplicates': summary['duplicate'],
            'warnings': sum(bool(r['warnings']) for r in reviewed)}, reviewed


def upload_import(user, test_id, filename, content, content_type):
    t = test_row(user, test_id, manage=True)
    name = validate_import_filename(filename, content_type)
    if name.rsplit('.', 1)[-1].lower() not in {'csv', 'xlsx', 'xls'}:
        raise AppError('Use CSV, XLSX or XLS', 422, 'UNSUPPORTED_FILE')
    strategy, rows, _ = parse_attendance_file(name, content, values_only=True)
    summary, reviewed = validate_import(rows, marks(user, test_id)['rows'], t['max_marks'])
    result = rpc(user, 'stage_faculty_test_import', {'p_test': str(test_id), 'p_filename': name,
                  'p_strategy': strategy, 'p_summary': summary, 'p_rows': reviewed})
    return review_import(user, result['import_id'])


def review_import(user, import_id, *, manage=False):
    faculty_context(user)
    item = read_one(get_admin_client().table('faculty_attendance_imports').select('*')
                    .eq('institution_id', str(user['institution_id'])).eq('import_id', str(import_id)).maybe_single())
    if not item or not item.get('test_id'):
        raise AppError('Import not found', 404, 'IMPORT_NOT_FOUND')
    test_row(user, item['test_id'], manage=manage)
    if manage and item['uploaded_by'] != str(user['user_id']):
        raise AppError('Import owner denied', 403, 'FORBIDDEN')
    item['rows'] = read_all(get_admin_client().table('faculty_attendance_import_rows').select(
        'row_number,raw_data,normalized_data,validation_status,errors,warnings').eq('import_id', str(import_id)).order('row_number'))
    return item


def correct_import(user, import_id, number, payload):
    item = review_import(user, import_id, manage=True)
    if item['status'] == 'IMPORTED' or not any(r['row_number'] == number for r in item['rows']):
        raise AppError('Staging row cannot be corrected', 409, 'IMPORT_NOT_EDITABLE')
    raw = [payload.data if r['row_number'] == number else r['raw_data'] for r in item['rows']]
    current = marks(user, item['test_id'])
    summary, rows = validate_import(raw, current['rows'], current['test']['max_marks'])
    rpc(user, 'review_faculty_test_import', {'p_import': str(import_id), 'p_updated_at': payload.expected_updated_at,
                                           'p_summary': summary, 'p_rows': rows})
    return review_import(user, import_id)


def commit_import(user, import_id, payload):
    item = review_import(user, import_id, manage=True)
    current = marks(user, item['test_id'])
    _, rows = validate_import([r['raw_data'] for r in item['rows']], current['rows'], current['test']['max_marks'])
    if any(row['errors'] for row in rows):
        raise AppError('Correct blocking issues before importing', 422, 'IMPORT_REVIEW_REQUIRED')
    return rpc(user, 'commit_faculty_test_import', {'p_import': str(import_id), 'p_updated_at': payload.expected_updated_at,
                                                  'p_version': payload.expected_version})


def history(user, test_id):
    test_row(user, test_id)
    db = get_admin_client()
    imports = read_all(db.table('faculty_attendance_imports').select(
        'import_id,original_filename,uploaded_by,status,summary,created_at,updated_at')
        .eq('institution_id', str(user['institution_id'])).eq('test_id', str(test_id)).order('created_at', desc=True).order('import_id'))
    events = read_all(db.table('admin_audit_log').select('action,actor_user_id,performed_at,record_data')
                     .eq('institution_id', str(user['institution_id'])).eq('table_name', 'faculty_tests')
                     .eq('record_id', str(test_id)).order('performed_at', desc=True).order('audit_id'))
    return {'imports': imports, 'events': events}
