"""Section-scoped student registration activity for the faculty Students pages."""

from uuid import UUID

from app.db.supabase import get_admin_client
from app.repositories.query_pages import read_all
from app.services.faculty_responsibilities import authorize_section

_ACTIONS = {
    'attendance.roster.create': 'roster_added',
    'attendance.roster.update': 'roster_updated',
    'attendance.roster.delete': 'roster_removed',
    'attendance.identity.reconcile': 'account_updated',
}


def registration_history(user: dict, section_id: UUID, *, limit: int = 25,
                         offset: int = 0, search: str = '') -> dict:
    authorize_section(user, section_id, 'attendance.read')
    tenant, section = str(user['institution_id']), str(section_id)
    db = get_admin_client()
    roster = read_all(db.table('faculty_attendance_rosters')
        .select('roster_id, student_name, register_number, university_roll_number, created_at')
        .eq('institution_id', tenant).eq('section_id', section).order('roster_id'))
    by_id = {str(row['roster_id']): row for row in roster}

    def audit_query():
        # Never grant the faculty account access to general institution audit logs.
        return (db.table('admin_audit_log')
            .select('audit_id, record_id, action, performed_at, record_data')
            .eq('institution_id', tenant).eq('table_name', 'faculty_attendance_rosters')
            .eq('status', 'success').in_('action', list(_ACTIONS))
            .order('performed_at', desc=True).order('audit_id'))

    # Snapshots retain section ownership after a roster record is removed.
    audits = {str(row['audit_id']): row for row in read_all(
        audit_query().eq('record_data->>section_id', section))}
    # A saved creation/removal snapshot also scopes older events whose payload
    # did not include the section. This preserves activity after removal.
    for entry in sorted(audits.values(), key=lambda row: row.get('performed_at') or '', reverse=True):
        data = entry.get('record_data') or {}
        if isinstance(data, dict) and (not data.get('institution_id') or str(data['institution_id']) == tenant):
            by_id.setdefault(str(entry['record_id']), data)
    ids = list(by_id)
    for start in range(0, len(ids), 100):
        for row in read_all(audit_query().in_('record_id', ids[start:start + 100])):
            audits[str(row['audit_id'])] = row

    events, additions = [], set()
    for entry in audits.values():
        data = entry.get('record_data')
        data = data if isinstance(data, dict) else {}
        roster_id = str(entry.get('record_id') or '')
        if data.get('section_id') and str(data['section_id']) != section:
            continue
        if data.get('institution_id') and str(data['institution_id']) != tenant:
            continue
        if roster_id not in by_id and str(data.get('section_id') or '') != section:
            continue
        identity = {**by_id.get(roster_id, {}), **data}
        action = _ACTIONS[entry['action']]
        if entry['action'] == 'attendance.identity.reconcile':
            action = ('identity_conflict' if data.get('conflict') else
                      'account_approved' if data.get('approval_status') == 'approved' else
                      'account_pending' if data.get('approval_status') == 'pending' else 'account_updated')
        if action == 'roster_added':
            additions.add(roster_id)
        events.append({
            'event_id': str(entry['audit_id']), 'roster_id': roster_id,
            'occurred_at': entry.get('performed_at'), 'action': action,
            'student_name': identity.get('student_name') or 'Student record',
            'register_number': identity.get('register_number'),
            'university_roll_number': identity.get('university_roll_number'),
        })

    # Older/imported roster additions have a durable creation timestamp even
    # when no per-student creation audit was written. Do not fabricate changes.
    for row in roster:
        roster_id = str(row['roster_id'])
        if roster_id in additions or not row.get('created_at'):
            continue
        events.append({
            'event_id': f'roster:{roster_id}', 'roster_id': roster_id,
            'occurred_at': row['created_at'],
            'action': 'roster_added',
            'student_name': row['student_name'], 'register_number': row['register_number'],
            'university_roll_number': row.get('university_roll_number'),
        })

    query = search.strip().casefold()
    events = [event for event in events if not query or any(query in str(event.get(key) or '').casefold()
              for key in ('student_name', 'register_number', 'university_roll_number'))]
    events.sort(key=lambda event: (event.get('occurred_at') or '', event['event_id']), reverse=True)
    return {'items': events[offset:offset + limit], 'total': len(events), 'limit': limit, 'offset': offset}
