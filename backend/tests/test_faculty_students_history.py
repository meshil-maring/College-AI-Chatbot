"""Registration activity must remain tenant- and section-scoped."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.services import faculty_students as service

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
OTHER_SECTION = '33333333-3333-4333-8333-333333333333'
USER = '44444444-4444-4444-8444-444444444444'


def principal():
    return {'user_id': USER, 'institution_id': TENANT, 'status': 'active', 'roles': ['faculty'],
            'effective_permissions': ['attendance.read', 'attendance.manage'],
            'role_assignments': [{'role': 'faculty', 'scope_type': 'institution', 'scope_id': TENANT}]}


class Query:
    def __init__(self, db, name):
        self.db, self.name, self.filters, self.bounds = db, name, [], None

    def select(self, _columns): return self
    def order(self, *_args, **_kwargs): return self
    def eq(self, column, value):
        def matches(row):
            if '->>' in column:
                parent, child = column.split('->>')
                data = row.get(parent)
                return isinstance(data, dict) and str(data.get(child)) == str(value)
            return str(row.get(column)) == str(value)
        self.filters.append(matches)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def range(self, start, end):
        self.bounds = (start, end)
        return self

    def execute(self):
        self.db.reads.append(self.name)
        rows = [row for row in self.db.tables.get(self.name, []) if all(check(row) for check in self.filters)]
        if self.bounds:
            rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


class Database:
    def __init__(self):
        self.tables = {'faculty_attendance_rosters': [], 'admin_audit_log': []}
        self.reads = []

    def table(self, name): return Query(self, name)


def roster(roster_id='r1', **extra):
    return {'roster_id': roster_id, 'institution_id': TENANT, 'section_id': SECTION,
            'student_name': 'Ada Rao', 'register_number': 'CS001', 'university_roll_number': 'UNI001',
            'created_at': '2026-10-19T08:00:00+00:00', **extra}


def audit(audit_id='a1', roster_id='r1', action='attendance.roster.create', data=None, **extra):
    return {'audit_id': audit_id, 'record_id': roster_id, 'institution_id': TENANT,
            'table_name': 'faculty_attendance_rosters', 'status': 'success', 'action': action,
            'performed_at': '2026-10-19T09:00:00+00:00', 'record_data': data or {}, **extra}


@pytest.fixture
def database(monkeypatch):
    db = Database()
    monkeypatch.setattr(service, 'get_admin_client', lambda: db)
    monkeypatch.setattr(service, 'authorize_section', lambda *_args: {'section_id': SECTION})
    return db


def test_history_includes_deleted_snapshots_and_scoped_legacy_updates_but_no_foreign_records(database):
    database.tables['faculty_attendance_rosters'] = [roster(), roster('foreign-section', section_id=OTHER_SECTION),
        roster('foreign-tenant', institution_id='other-tenant')]
    database.tables['admin_audit_log'] = [
        audit(data=roster()),
        audit('update', action='attendance.roster.update', data={'student_name': 'Ada Updated'}),
        audit('delete', 'deleted', 'attendance.roster.delete', roster('deleted', student_name='Removed student')),
        audit('deleted-update', 'deleted', 'attendance.roster.update', {'student_name': 'Earlier name'}),
        audit('foreign-1', 'foreign-section', data=roster('foreign-section', section_id=OTHER_SECTION, student_name='Private name')),
        audit('foreign-2', data=roster(), institution_id='other-tenant'),
        audit('foreign-3', action='attendance.roster.update', data=roster(section_id=OTHER_SECTION)),
        audit('unrelated', action='user.password.reset', data=roster()),
        audit('failed', data=roster(), status='failure'),
    ]
    result = service.registration_history(principal(), UUID(SECTION))
    assert {event['event_id'] for event in result['items']} == {'a1', 'update', 'delete', 'deleted-update'}
    assert result['total'] == 4
    assert next(event for event in result['items'] if event['event_id'] == 'update')['student_name'] == 'Ada Updated'
    assert next(event for event in result['items'] if event['event_id'] == 'delete')['action'] == 'roster_removed'
    assert 'Private name' not in str(result)


def test_creation_fallback_uses_saved_timestamps_and_does_not_duplicate_creation_audits(database):
    database.tables['faculty_attendance_rosters'] = [roster(), roster('imported', source_metadata={'import_id': 'upload'}),
        roster('older'), roster('no-date', created_at=None)]
    database.tables['admin_audit_log'] = [audit(data=roster())]
    result = service.registration_history(principal(), UUID(SECTION))
    assert result['total'] == 3
    assert len([event for event in result['items'] if event['roster_id'] == 'r1']) == 1
    imported = next(event for event in result['items'] if event['roster_id'] == 'imported')
    assert imported['action'] == 'roster_added'
    assert imported['occurred_at'] == '2026-10-19T08:00:00+00:00'


@pytest.mark.parametrize('data,expected', [
    ({'approval_status': 'approved'}, 'account_approved'),
    ({'approval_status': 'pending'}, 'account_pending'),
    ({'approval_status': 'approved', 'conflict': True}, 'identity_conflict'),
    ({'approval_status': 'rejected'}, 'account_updated'),
])
def test_account_reconciliation_is_reported_as_registration_activity(database, data, expected):
    database.tables['faculty_attendance_rosters'] = [roster()]
    database.tables['admin_audit_log'] = [audit(action='attendance.identity.reconcile', data=data)]
    result = service.registration_history(principal(), UUID(SECTION))
    assert next(event for event in result['items'] if event['event_id'] == 'a1')['action'] == expected


def test_history_search_and_pagination_apply_after_scoping_and_sorting(database):
    database.tables['faculty_attendance_rosters'] = [roster()]
    database.tables['admin_audit_log'] = [audit('first', data=roster()), audit('latest', action='attendance.roster.update',
        data={'student_name': 'Ada Updated'}, performed_at='2026-10-19T10:00:00+00:00')]
    first = service.registration_history(principal(), UUID(SECTION), search='uni001', limit=1)
    second = service.registration_history(principal(), UUID(SECTION), search='UNI001', limit=1, offset=1)
    assert first['total'] == second['total'] == 2
    assert first['items'][0]['event_id'] == 'latest'
    assert second['items'][0]['event_id'] == 'first'
    assert service.registration_history(principal(), UUID(SECTION), search='missing')['items'] == []


def test_history_projects_only_registration_fields(database):
    database.tables['admin_audit_log'] = [audit(data=roster(email='private@example.com', address='private address',
        access_token='secret', notes='private notes'), ip_address='private IP', user_agent='private agent')]
    event = service.registration_history(principal(), UUID(SECTION))['items'][0]
    assert set(event) == {'event_id', 'roster_id', 'occurred_at', 'action', 'student_name', 'register_number', 'university_roll_number'}
    assert 'private' not in str(event) and 'secret' not in str(event)


def test_history_rejects_invalid_scope_before_reading_any_database_rows(monkeypatch):
    def deny(*_args):
        raise AppError('Denied', 403, 'FACULTY_SCOPE_DENIED')
    client = MagicMock()
    monkeypatch.setattr(service, 'authorize_section', deny)
    monkeypatch.setattr(service, 'get_admin_client', client)
    with pytest.raises(AppError) as error:
        service.registration_history(principal(), UUID(OTHER_SECTION))
    assert error.value.status_code == 403
    client.assert_not_called()


def test_history_handles_multiple_internal_database_pages(database):
    database.tables['admin_audit_log'] = [audit(str(index), str(index), data=roster(str(index))) for index in range(510)]
    result = service.registration_history(principal(), UUID(SECTION), limit=25, offset=500)
    assert result['total'] == 510 and len(result['items']) == 10


def test_history_api_paginates_and_rejects_invalid_inputs(monkeypatch):
    from app.api import faculty as api
    from app.main import app
    reader = MagicMock(return_value={'items': [], 'total': 0})
    monkeypatch.setattr(service, 'registration_history', reader)
    app.dependency_overrides[api._FACULTY] = principal
    try:
        client = TestClient(app)
        url = f'/api/v1/faculty/attendance/sections/{SECTION}/registration-history'
        assert client.get(url + '?limit=10&offset=20&search=Ada').status_code == 200
        reader.assert_called_once_with(principal(), UUID(SECTION), limit=10, offset=20, search='Ada')
        for query in ['limit=0', 'limit=101', 'offset=-1', 'search=' + 'x' * 129]:
            assert client.get(url + '?' + query).status_code == 422
        assert reader.call_count == 1
    finally:
        app.dependency_overrides.pop(api._FACULTY, None)
