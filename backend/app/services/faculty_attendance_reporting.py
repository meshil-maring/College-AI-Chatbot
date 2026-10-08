"""Authorized projections of recorded attendance, never imported percentages."""

from collections import Counter
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all, read_one
from app.services.authorization import effective_authorization
from app.services.faculty_responsibilities import authorize_section, faculty_context
from app.services.phase81_rbac import _active_sections

ROSTER_FIELDS = ('roster_id', 'register_number', 'university_roll_number', 'student_name',
                 'email', 'roster_status', 'linked_student_id', 'reconciliation_state')

# The project's EXISTING attendance monitoring threshold (percent). Used by
# the faculty section overview, the delegated responsibilities report and the
# student academic experience. One constant so every surface reports the same
# policy value; no new threshold is introduced anywhere.
MONITORING_THRESHOLD = 75


def resources(user: dict) -> list[dict]:
    context = faculty_context(user)
    teaching = context['teaching_assignments']
    result = []
    for section in _active_sections(UUID(str(user['institution_id']))):
        if effective_authorization(user, section, 'attendance.read', teaching=teaching,
                                   responsibilities=context['responsibilities']):
            result.append({**section, 'can_manage': effective_authorization(
                user, section, 'attendance.manage', teaching=teaching, responsibilities=[])})
    return result


def statistics(records: list[dict]) -> dict:
    counts = Counter(str(r.get('status', '')).strip().lower() for r in records)
    percentage = round(100 * counts['present'] / len(records), 2) if records else None
    return {'record_count': len(records), 'present': counts['present'], 'absent': counts['absent'],
            'late': counts['late'], 'excused': counts['excused'], 'attendance_percentage': percentage,
            'low_attendance': percentage is not None and percentage < MONITORING_THRESHOLD}


def section_data(user: dict, section_id: UUID) -> tuple[dict, list[dict], list[dict], list[dict]]:
    section = authorize_section(user, section_id, 'attendance.read')
    db = get_admin_client()
    tenant = str(user['institution_id'])
    roster = read_all(db.table('faculty_attendance_rosters').select(','.join(ROSTER_FIELDS))
                      .eq('institution_id', tenant).eq('section_id', str(section_id)).order('roster_id'))
    sessions = read_all(db.table('faculty_attendance_sessions').select('session_id, session_date, conducted_by')
                        .eq('institution_id', tenant).eq('section_id', str(section_id)).order('session_id'))
    dates = {s['session_id']: s['session_date'] for s in sessions}
    records = []
    ids = list(dates)
    for start in range(0, len(ids), 100):
        batch = read_all(db.table('faculty_attendance_records').select('record_id, session_id, roster_id, status')
                         .in_('session_id', ids[start:start + 100]).order('record_id'))
        records.extend({**r, 'session_date': dates[r['session_id']]} for r in batch)
    # Existing admin/student attendance is preserved. Mirrored Faculty records
    # are deduplicated by linked identity + date, not counted twice.
    legacy = read_all(db.table('student_attendance').select('student_attendance_id, student_id, date, status')
                     .eq('institution_id', tenant).eq('section_id', str(section_id)).order('student_attendance_id'))
    linked = {r['linked_student_id']: r['roster_id'] for r in roster if r.get('linked_student_id') and r.get('reconciliation_state') != 'CONFLICT'}
    seen = {(r['roster_id'], r['session_date']) for r in records}
    for record in legacy:
        roster_id = linked.get(record['student_id'])
        if roster_id and (roster_id, record['date']) not in seen:
            records.append({'record_id': record['student_attendance_id'], 'roster_id': roster_id,
                            'session_date': record['date'], 'status': record['status'], 'session_id': None})
    by_roster: dict[str, list[dict]] = {}
    for record in records:
        by_roster.setdefault(record['roster_id'], []).append(record)
    students = [{**r, **statistics(by_roster.get(r['roster_id'], []))} for r in roster]
    return section, students, sessions, records


def overview(user: dict, section_id: UUID) -> dict:
    section, students, sessions, records = section_data(user, section_id)
    by_date: dict[str, list[dict]] = {}
    for record in records:
        by_date.setdefault(record['session_date'], []).append(record)
    dates = set(by_date) | {s['session_date'] for s in sessions}
    return {'section': section, 'total_students': len(students), 'session_count': len(dates),
            **statistics(records), 'average_attendance': statistics(records)['attendance_percentage'],
            'low_attendance_count': sum(s['low_attendance'] for s in students), 'monitoring_threshold': MONITORING_THRESHOLD,
            'trend': [{'date': date, **statistics(by_date.get(date, []))} for date in sorted(dates)]}


def students_page(user: dict, section_id: UUID, *, limit: int = 50, offset: int = 0,
                  search: str = '', registration: str | None = None, low_only: bool = False,
                  sort: str = 'register_number', descending: bool = False) -> dict:
    _, students, _, _ = section_data(user, section_id)
    query = search.strip().casefold()
    students = [s for s in students if (not query or any(query in str(s.get(k) or '').casefold()
                 for k in ('register_number', 'university_roll_number', 'student_name', 'email')))
                and (not registration or s['roster_status'] == registration)
                and (not low_only or s['low_attendance'])]
    students.sort(key=lambda s: (s.get(sort) is None, s.get(sort) if s.get(sort) is not None else '', s['roster_id']), reverse=descending)
    return {'items': students[offset:offset + limit], 'total': len(students), 'limit': limit, 'offset': offset}


def student_profile(user: dict, roster_id: UUID, *, limit: int = 50, offset: int = 0) -> dict:
    row = read_one(get_admin_client().table('faculty_attendance_rosters').select('section_id')
                   .eq('institution_id', str(user['institution_id'])).eq('roster_id', str(roster_id)).maybe_single())
    if not row:
        raise AppError('Student attendance not found', 404, 'ROSTER_NOT_FOUND')
    section, students, _, records = section_data(user, UUID(row['section_id']))
    student = next((s for s in students if s['roster_id'] == str(roster_id)), None)
    if student is None:
        raise AppError('Student attendance not found', 404, 'ROSTER_NOT_FOUND')
    history = sorted((r for r in records if r['roster_id'] == str(roster_id)), key=lambda r: (r['session_date'], r['record_id']), reverse=True)
    return {'student': student, 'section': section, 'history': history[offset:offset + limit], 'total': len(history)}


def sessions_page(user: dict, section_id: UUID, *, limit: int = 50, offset: int = 0) -> dict:
    _, _, sessions, records = section_data(user, section_id)
    by_date: dict[str, list[dict]] = {}
    for record in records:
        by_date.setdefault(record['session_date'], []).append(record)
    session_dates = {s['session_date']: s for s in sessions}
    rows = [{**session_dates.get(date, {'session_id': None, 'session_date': date}),
             **statistics(by_date.get(date, []))} for date in sorted(set(session_dates) | set(by_date), reverse=True)]
    return {'items': rows[offset:offset + limit], 'total': len(rows)}
