"""Isolated HTTP and RPC fixtures; external I/O is never used."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.knowledge import resources, resource_uploads
from app.main import app
from app.services.knowledge.resources import operations

TENANT = '10000000-0000-0000-0000-000000000001'
ACTOR = '20000000-0000-0000-0000-000000000001'
SOURCE = '30000000-0000-0000-0000-000000000001'
REVISION = '40000000-0000-0000-0000-000000000001'
VERSION = '50000000-0000-0000-0000-000000000001'
DOCUMENT = '60000000-0000-0000-0000-000000000001'


class DatabaseFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__('Private database detail must never reach clients')


@pytest.fixture
def user():
    return {'user_id': ACTOR, 'institution_id': TENANT, 'roles': ['staff'],
        'permissions_resolved': True, 'effective_permissions': ['ai.knowledge.create', 'documents.create'],
        'authorization_context': SimpleNamespace(role='staff')}


@pytest.fixture
def revision():
    return {'knowledge_source_id': SOURCE, 'revision_id': REVISION, 'institution_id': TENANT,
        'revision_number': 1, 'revision_version': 4, 'title': 'Student guide', 'description': None,
        'source_type': 'handbook', 'visibility': 'restricted', 'lifecycle_status': 'draft',
        'created_by_user_id': ACTOR, 'created_at': '2026-10-28T10:00:00Z',
        'updated_at': '2026-10-28T10:00:00Z', 'policy_version': 0,
        'audience_roles': ['student'], 'documents': [], 'storage_object_key': 'hidden/file.pdf'}


@pytest.fixture
def database(monkeypatch, revision):
    database = MagicMock()

    def rpc(name, parameters):
        if name.startswith('read_knowledge_'):
            data = {'items': [revision], 'total': 1}
        elif name in {'save_knowledge_draft', 'decide_knowledge_revision', 'read_resource_chat_context'}:
            data = revision
        else:
            raise AssertionError('Unexpected database operation: ' + name)
        return MagicMock(execute=MagicMock(return_value=SimpleNamespace(data=data)))

    database.rpc.side_effect = rpc
    monkeypatch.setattr(operations, 'get_admin_client', lambda: database)
    return database


@pytest.fixture
def client(user, database):
    overrides = {resources._WRITE: lambda: user, resources._READ: lambda: user,
        resource_uploads._WRITE: lambda: user}
    app.dependency_overrides.update(overrides)
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        for dependency in overrides:
            app.dependency_overrides.pop(dependency, None)
