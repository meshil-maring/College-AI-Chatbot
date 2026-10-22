"""Faculty examination routes regressions with database doubles."""

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


@pytest.fixture
def api():
    app.dependency_overrides[faculty] = user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(faculty, None)



@pytest.mark.parametrize('field', ['institution_id', 'faculty_id', 'student_id', 'section_id', 'role', 'test_id'])
def test_api_create_rejects_forged_authority(api, field):
    response = api.post(f'/api/v1/faculty/tests/sections/{SECTION}', json={'title': 'Test', 'test_type': 'internal', 'max_marks': 100, field: OTHER})
    assert response.status_code == 422



@pytest.mark.parametrize('method,path,payload', [
    ('get', f'/{TEST}', None), ('get', f'/{TEST}/history', None),
    ('post', f'/{TEST}/transition', {'expected_version': 1, 'action': 'publish'}),
    ('put', f'/{TEST}/marks', {'expected_version': 1, 'rows': [{'roster_id': ROSTER, 'mark_status': 'absent'}]}),
    ('post', f'/{TEST}/corrections', {'expected_version': 1, 'rows': [{'roster_id': ROSTER, 'mark_status': 'absent'}], 'reason': 'Verified correction'}),
])
def test_api_independently_denies_scope(api, monkeypatch, method, path, payload):
    def deny(*_args, **_kwargs):
        raise AppError('Scope denied', 403, 'FACULTY_SCOPE_DENIED')
    monkeypatch.setattr(svc, 'test_row', deny)
    response = api.request(method, '/api/v1/faculty/tests' + path, json=payload)
    assert response.status_code == 403
