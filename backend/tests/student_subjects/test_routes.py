import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.admin import common
from app.api.admin.student_records import student_workspace
from app.api.admin.dependencies import _authorize_admin_endpoint
from app.api.faculty.registrations import router as faculty_router
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.services.auth import authorization
from app.services.faculty import faculty_responsibilities
from app.services.students import subject_assignments
from .support import Database, OTHER, REGISTRATION, SECTION, SCOPE, TENANT, USER, principal


@pytest.fixture
def api(monkeypatch):
    db, actor, audits = Database(), principal('admin'), []
    for module in (authorization, faculty_responsibilities, subject_assignments):
        monkeypatch.setattr(module, 'get_admin_client', lambda: db)
    monkeypatch.setattr(authorization.tenancy_repo, 'get_institution_by_id', lambda *_: {'status': 'active', 'is_active': True})
    monkeypatch.setattr(faculty_responsibilities, '_active_sections', lambda *_: [{**SCOPE, 'institution_id': TENANT}])
    monkeypatch.setattr(faculty_responsibilities, 'list_responsibilities', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(common, 'record_audit', lambda *args: audits.append(args))
    db.tables['faculty_section_assignments'] = [{'faculty_user_id': USER, 'institution_id': TENANT,
        'section_id': SECTION, 'is_active': True, 'start_at': '2020-01-01T00:00:00Z'}]
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(student_workspace.router, dependencies=[Depends(_authorize_admin_endpoint)])
    app.include_router(faculty_router, prefix='/faculty')
    app.dependency_overrides[get_current_user] = lambda: actor
    return TestClient(app), db, actor, audits


def path(panel='admin', section=SECTION):
    prefix = '/admin/student-workspace' if panel == 'admin' else '/faculty/student-registrations'
    return f'{prefix}/sections/{section}/subject-assignments'


def test_admin_assignment_uses_server_scope_and_records_audit_once(api):
    client, db, _, audits = api
    assert client.get(path()).json()['total'] == 1
    response = client.post(f'{path()}/{REGISTRATION}?institution_id={OTHER}')
    assert response.status_code == 200, response.text
    assert db.writes[0][1]['institution_id'] == TENANT
    assert client.get(path()).json()['total'] == 0
    assert client.post(f'{path()}/{REGISTRATION}').json()['status'] == 'already_assigned'
    assert audits == []
    assert db.audits == ['students.subject.assign']
    assert len(db.rpc_calls) == 1


def test_faculty_assignment_requires_an_active_teaching_assignment(api):
    client, db, actor, _ = api
    actor.update(principal())
    assert client.get(path('faculty')).json()['total'] == 1
    db.tables['faculty_section_assignments'][0]['end_at'] = '2020-01-02T00:00:00Z'
    assert client.post(f'{path("faculty")}/{REGISTRATION}').status_code == 403
    assert not db.writes
    db.tables['faculty_section_assignments'][0].pop('end_at')
    assert client.post(f'{path("faculty")}/{REGISTRATION}').status_code == 200


@pytest.mark.parametrize('permission', ['students.read', 'students.create'])
def test_admin_assignment_permissions_are_enforced_by_route_policy(api, permission):
    client, db, actor, _ = api
    actor['effective_permissions'].remove(permission)
    assert client.post(f'{path()}/{REGISTRATION}').status_code == 403
    assert not db.writes


@pytest.mark.parametrize('panel,role', [('admin', 'faculty'), ('admin', 'staff'), ('faculty', 'admin'), ('faculty', 'student')])
def test_role_boundaries_apply_even_with_wildcard_permissions(api, panel, role):
    client, db, actor, _ = api
    actor.update(principal(role))
    actor['effective_permissions'] = ['*']
    assert client.get(path(panel)).status_code == 403
    assert client.post(f'{path(panel)}/{REGISTRATION}').status_code == 403
    assert not db.writes


def test_foreign_section_and_invalid_pagination_are_rejected(api):
    client, db, _, _ = api
    assert client.get(path(section=OTHER)).status_code == 403
    assert client.post(f'{path(section=OTHER)}/{REGISTRATION}').status_code == 403
    assert client.get(path() + '?limit=0').status_code == 422
    assert client.get(path() + '?offset=-1').status_code == 422
    assert not db.writes
