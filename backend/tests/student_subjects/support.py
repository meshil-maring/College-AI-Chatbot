from types import SimpleNamespace

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
REGISTRATION = '44444444-4444-4444-8444-444444444444'
OTHER = '55555555-5555-4555-8555-555555555555'
SCOPE = {'section_id': SECTION, 'program_id': 'program', 'academic_year_id': 'year',
         'semester_id': 'semester', 'section_code': 'A', 'course_offering_id': 'offering'}


def registration(**changes):
    return {'registration_id': REGISTRATION, 'institution_id': TENANT, 'program_id': 'program',
            'academic_year_id': 'year', 'semester_id': 'semester', 'section_code': 'A',
            'batch_id': 'batch', 'batch_start_year': 2026, 'batch_end_year': 2030,
            'student_name': 'Ada Rao', 'register_number': 'CS001', 'university_roll_number': None,
            'email': 'ada@college.edu', **changes}


def principal(role='faculty'):
    return {'user_id': USER, 'institution_id': TENANT, 'roles': [role], 'status': 'active',
            'permissions_resolved': True, 'effective_permissions': ['students.read', 'students.create', 'attendance.manage'],
            'role_assignments': [{'role': role, 'scope_type': 'institution', 'scope_id': TENANT, 'is_active': True}]}


class Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.bounds, self.data = db, table, [], None, None

    def select(self, *_): return self
    def eq(self, key, value):
        self.filters.append(lambda row: str(row.get(key)) == str(value))
        return self
    def in_(self, key, values):
        self.filters.append(lambda row: row.get(key) in values)
        return self
    def order(self, *_args, **_kwargs): return self
    def range(self, start, end):
        self.bounds = (start, end)
        return self
    def insert(self, data):
        self.data = data
        return self

    def execute(self):
        self.db.reads.append(self.table)
        if self.data is not None:
            if self.db.error:
                raise self.db.error
            row = {'roster_id': 'new-roster', **self.data}
            self.db.writes.append((self.table, row))
            self.db.tables.setdefault(self.table, []).append(row)
            return SimpleNamespace(data=[row])
        rows = [row for row in self.db.tables.get(self.table, []) if all(check(row) for check in self.filters)]
        if self.bounds:
            rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


class Database:
    def __init__(self):
        self.tables = {'student_registrations': [registration()],
                       'semesters': [{'semester_id': 'semester', 'semester_number': 1}]}
        self.reads, self.writes, self.audits, self.rpc_calls, self.error = [], [], [], [], None

    def table(self, name):
        return Query(self, name)

    def rpc(self, name, fields):
        """Model the atomic RPC result; these doubles do not test SQL internals."""
        self.rpc_calls.append((name, fields))
        assert name == 'assign_student_subject'
        def execute():
            if self.error:
                raise self.error
            saved = next(row for row in self.tables['student_registrations']
                         if row['registration_id'] == fields['p_registration_id'])
            student = next((row for row in self.tables.get('students', [])
                            if row['register_number'] == saved['register_number']), None)
            approved = student and student.get('approval_status') == 'approved'
            state = 'UNREGISTERED' if not student else 'PENDING_APPROVAL' if not approved else 'ACTIVE' if student.get('is_active') else 'INACTIVE'
            row = {key: saved.get(key) for key in ('register_number', 'university_roll_number', 'student_name', 'email')}
            row.update(roster_id='new-roster', institution_id=fields['p_institution_id'],
                       section_id=fields['p_section_id'], course_offering_id=SCOPE['course_offering_id'],
                       roster_status=state, linked_student_id=student['student_id'] if approved else None)
            self.writes.append(('faculty_attendance_rosters', row))
            self.tables.setdefault('faculty_attendance_rosters', []).append(row)
            self.audits.append('students.subject.assign')
            return SimpleNamespace(data={'registration_id': fields['p_registration_id'],
                                         'roster_id': row['roster_id'], 'status': 'assigned'})
        return SimpleNamespace(execute=execute)
