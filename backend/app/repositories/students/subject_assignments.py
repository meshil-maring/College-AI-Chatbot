"""Tenant-scoped class records and subject memberships."""

from app.repositories.shared.query_pages import read_all, read_rows


def registration(db, tenant: str, scope: dict, registration_id: str) -> dict | None:
    query = (db.table('student_registrations').select('*')
             .eq('institution_id', tenant).eq('registration_id', registration_id)
             .eq('section_code', scope.get('section_code') or scope['code']))
    for field in ('program_id', 'academic_year_id', 'semester_id'):
        query = query.eq(field, str(scope[field]))
    rows = read_rows(query.range(0, 0))
    return rows[0] if rows else None


def roster(db, tenant: str, section_id: str) -> list[dict]:
    return read_all(db.table('faculty_attendance_rosters')
                    .select('roster_id, register_number, university_roll_number, linked_student_id, reconciliation_state')
                    .eq('institution_id', tenant).eq('section_id', section_id).order('roster_id'))


def semester_number(db, semester_id: str) -> int | None:
    rows = read_rows(db.table('semesters').select('semester_number')
                     .eq('semester_id', semester_id).range(0, 0))
    return rows[0]['semester_number'] if rows else None
