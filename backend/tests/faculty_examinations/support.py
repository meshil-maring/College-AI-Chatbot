"""Assessment contracts; actual transactions and races are exercised in Docker."""

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

TENANT = '11111111-1111-4111-8111-111111111111'
SECTION = '22222222-2222-4222-8222-222222222222'
ACTOR = '33333333-3333-4333-8333-333333333333'
ROSTER = '44444444-4444-4444-8444-444444444444'
TEST = '55555555-5555-4555-8555-555555555555'
OTHER = '66666666-6666-4666-8666-666666666666'


def user():
    return {'user_id': ACTOR, 'institution_id': TENANT, 'status': 'active', 'roles': ['faculty'],
            'effective_permissions': ['results.read', 'results.manage'],
            'role_assignments': [{'role': 'faculty', 'scope_type': 'institution', 'scope_id': TENANT}]}


def roster(**extra):
    return {'roster_id': ROSTER, 'register_number': 'R1', 'university_roll_number': 'U1',
            'student_name': 'Student', 'roster_status': 'ACTIVE', 'reconciliation_state': 'LINKED', **extra}


def assessment(**extra):
    return {'test_id': TEST, 'section_id': SECTION, 'institution_id': TENANT, 'created_by': ACTOR,
            'status': 'COMPLETED', 'marks_state': 'DRAFT', 'max_marks': 100, 'passing_marks': 40, 'version': 3, **extra}


def teaching(**extra):
    return {'section_id': SECTION, 'faculty_user_id': ACTOR, 'institution_id': TENANT, 'is_active': True,
            'start_at': (datetime.now(UTC) - timedelta(days=1)).isoformat(), **extra}

