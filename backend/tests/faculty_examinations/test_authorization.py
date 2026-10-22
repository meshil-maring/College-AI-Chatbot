"""Faculty examination authorization regressions with database doubles."""

import struct
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.api.faculty.faculty_tests import faculty
from app.core.errors import AppError
from app.main import app
from app.schemas.faculty.faculty_tests import Correction, MarkInput, MarksCommand, Transition
from app.schemas.faculty.faculty_tests import TestInput as AssessmentInput
from app.services.faculty import faculty_tests as svc
from app.services.students import student_results
from app.services.auth.authorization import effective_authorization
from app.services.faculty.faculty_attendance import ParsedRows


from .support import TENANT, SECTION, ACTOR, ROSTER, TEST, OTHER, user, roster, assessment, teaching


@pytest.mark.parametrize('change', [{'section_id': OTHER}, {'institution_id': OTHER}, {'is_active': False}, {'revoked_at': '2026-01-01T00:00:00Z'},
                                  {'end_at': '2020-01-01T00:00:00Z'}, {'start_at': '2099-01-01T00:00:00Z'}, {'faculty_user_id': OTHER}])
def test_teaching_boundary_fails_closed(change):
    assert not effective_authorization(user(), {'section_id': SECTION, 'institution_id': TENANT}, 'results.manage',
                                       teaching=[teaching(**change)], responsibilities=[])



@pytest.mark.parametrize('kind,change,allowed', [
    ('department', {}, True), ('department', {'department_id': OTHER}, False),
    ('section', {}, True), ('section', {'section_code': 'B'}, False),
    ('section', {'program_id': OTHER}, False), ('section', {'semester_id': OTHER}, False),
    ('section', {'academic_year_id': OTHER}, False), ('department', {'institution_id': OTHER}, False),
])
def test_responsibility_monitoring_scope(kind, change, allowed):
    resource = {'institution_id': TENANT, 'section_id': SECTION, 'department_id': 'dept', 'program_id': 'program',
                'academic_year_id': 'year', 'semester_id': 'semester', 'section_code': 'A'}
    appointment = {**teaching(), **resource, 'scope_type': kind, 'permissions': ['results.read'], **change}
    assert effective_authorization(user(), resource, 'results.read', teaching=[], responsibilities=[appointment]) is allowed
    assert not effective_authorization(user(), resource, 'results.manage', teaching=[], responsibilities=[appointment])



def test_resource_capabilities_separate_monitoring_and_teaching(monkeypatch):
    sections = [{'section_id': SECTION, 'institution_id': TENANT}, {'section_id': OTHER, 'institution_id': TENANT}]
    monkeypatch.setattr(svc, '_active_sections', lambda _: sections)
    monkeypatch.setattr(svc, 'faculty_context', lambda _: {'teaching_assignments': [teaching()], 'responsibilities': []})
    assert svc.resources(user()) == [{**sections[0], 'can_manage': True}]



def test_rpc_actor_tenant_are_always_server_derived(monkeypatch):
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {'saved': 1}
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    assert svc.rpc(user(), 'save_faculty_test_marks', {'p_actor': OTHER, 'p_tenant': OTHER}) == {'saved': 1}
    assert db.rpc.call_args.args[1]['p_actor'] == ACTOR
    assert db.rpc.call_args.args[1]['p_tenant'] == TENANT



@pytest.mark.parametrize('code,status', [('42501', 403), ('P0002', 404), ('40001', 409), ('23505', 409), ('23514', 422), ('23503', 422)])
def test_database_failures_are_mapped_without_schema_leaks(monkeypatch, code, status):
    db = MagicMock()
    db.rpc.return_value.execute.side_effect = APIError({'code': code, 'message': 'internal schema details', 'details': None, 'hint': None})
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as caught:
        svc.rpc(user(), 'save_faculty_test', {})
    assert caught.value.status_code == status and 'internal schema' not in str(caught.value)



def test_unknown_or_foreign_test_is_not_disclosed(monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(data=None)
    monkeypatch.setattr(svc, 'faculty_context', lambda _: {})
    monkeypatch.setattr(svc, 'get_admin_client', lambda: db)
    with pytest.raises(AppError) as caught:
        svc.test_row(user(), OTHER)
    assert caught.value.status_code == 404
