"""Current assessment membership with preserved previously entered marks."""

from decimal import Decimal

from app.repositories.shared.query_pages import read_all
from app.services.academics import managed_rosters

def marks(user, test_id, *, db, t, identity_candidates, identity_match, review):
    roster = read_all(db.table('faculty_attendance_rosters').select(
        'roster_id,register_number,university_roll_number,student_name,roster_status,reconciliation_state,linked_student_id,participation_active,participation_ended_at')
        .eq('institution_id', str(user['institution_id'])).eq('section_id', t['section_id']).order('register_number').order('roster_id'))
    candidates = identity_candidates(db, str(user['institution_id']), roster)
    managed = managed_rosters.contexts(db, str(user['institution_id']), roster)
    for r in roster:
        identity, errors = identity_match(str(user['institution_id']), r, candidates)
        identity, scope_errors = managed_rosters.academic_identity(identity, r, t.get('section', {}), managed)
        errors.extend(scope_errors)
        if errors or (identity and any(identity.get(key) is not None and str(identity[key]) != str(t['section'][key])
                                     for key in ('program_id', 'academic_year_id'))) or (
            r.get('linked_student_id') and str(r['linked_student_id']) != str((identity or {}).get('student_id'))
        ):
            r['reconciliation_state'] = 'CONFLICT'
        r.pop('linked_student_id', None)
    saved = read_all(db.table('test_results').select('roster_id,scored_marks,mark_status,remarks,percentage')
                    .eq('institution_id', str(user['institution_id'])).eq('test_id', str(test_id)).order('test_result_id'))
    by_id = {row['roster_id']: row for row in saved}
    t['can_edit_metadata'] = t['can_manage'] and t['status'] in ('DRAFT', 'SCHEDULED') and not saved
    rows = [{**r, **by_id.get(r['roster_id'], {'scored_marks': None, 'mark_status': 'missing', 'remarks': None, 'percentage': None})}
            for r in roster if (r['roster_status'] != 'INACTIVE' and r.get('participation_active', True)) or r['roster_id'] in by_id]
    for row in rows:
        row['outcome'] = ('pass' if Decimal(str(row['scored_marks'])) >= Decimal(str(t['passing_marks'])) else 'fail') \
            if row['mark_status'] == 'present' and t['passing_marks'] is not None else None
    return {'test': t, 'rows': rows, 'review': review(rows)}

