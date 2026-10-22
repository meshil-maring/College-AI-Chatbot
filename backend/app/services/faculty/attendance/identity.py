"""Exact tenant-local identifier matching for academic membership writers."""

from app.repositories.shared.query_pages import read_all
from app.services.faculty.attendance.row_format import _clean

def match_identity(institution_id: str, row: dict, candidates: list[dict]) -> tuple[dict | None, list[str]]:
    """Exact tenant-local identifiers; ambiguity or disagreement never merges."""
    register, roll = _clean(row.get('register_number')), _clean(row.get('university_roll_number'))
    matches = [s for s in candidates if str(s.get('institution_id')) == institution_id and
               ((register and s.get('register_number') == register) or (roll and s.get('university_roll_number') == roll))]
    unique = {s['student_id']: s for s in matches}
    if len(unique) > 1:
        return None, ['Identifiers match duplicate or conflicting student candidates']
    student = next(iter(unique.values()), None)
    if student and ((register and student.get('register_number') and register != student['register_number']) or
                    (roll and student.get('university_roll_number') and roll != student['university_roll_number'])):
        return None, ['Provided identifiers conflict with the matched student']
    return student, []


def _identity_candidates(db, tenant: str, rows: list[dict]) -> list[dict]:
    candidates = {}
    for column in ('register_number', 'university_roll_number'):
        ids = sorted({_clean(row.get(column)) for row in rows if _clean(row.get(column))})
        for start in range(0, len(ids), 100):
            for student in read_all(db.table('students').select('student_id, institution_id, register_number, university_roll_number, approval_status, is_active, status, program_id, academic_year_id')
                                    .eq('institution_id', tenant).in_(column, ids[start:start + 100]).order('student_id')):
                candidates[student['student_id']] = student
    return list(candidates.values())


