"""HTTP contracts pin actors to identity and expose only safe resource data."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.knowledge.resources import uploads
from .conftest import ACTOR, TENANT, SOURCE, REVISION, VERSION, DatabaseFailure


def test_create_draft_uses_server_actor_and_audience_mapping(client, database):
    response = client.post('/api/v1/knowledge/resources', json={
        'title': 'Student guide', 'source_type': 'handbook',
        'audience': {'mode': 'roles', 'roles': ['student', 'faculty']},
    })
    assert response.status_code == 201
    operation, parameters = database.rpc.call_args.args
    assert operation == 'save_knowledge_draft'
    assert parameters['actor'] == ACTOR and parameters['tenant'] == TENANT
    assert parameters['payload']['visibility'] == 'restricted'
    assert parameters['payload']['audience_roles'] == ['student', 'faculty']
    assert 'storage_object_key' not in response.json()


def test_resource_chat_context_uses_trusted_identity_and_safe_projection(client, database):
    response = client.get(f'/api/v1/knowledge/resources/{SOURCE}/chat-context')
    assert response.status_code == 200
    operation, parameters = database.rpc.call_args.args
    assert operation == 'read_resource_chat_context'
    assert parameters == {'actor': ACTOR, 'tenant': TENANT, 'source_id': SOURCE}
    assert set(response.json()) == {'knowledge_source_id', 'title', 'available'}


@pytest.mark.parametrize('extra', [{'institution_id': TENANT}, {'created_by_user_id': ACTOR}, {'lifecycle_status': 'published'}])
def test_create_rejects_server_owned_fields(client, database, extra):
    response = client.post('/api/v1/knowledge/resources', json={'title': 'Guide', 'source_type': 'handbook', **extra})
    assert response.status_code == 422
    database.rpc.assert_not_called()


@pytest.mark.parametrize('audience', [
    {'mode': 'public', 'roles': ['student']}, {'mode': 'roles', 'roles': ['teacher']},
    {'mode': 'roles', 'roles': ['staff', 'staff']},
])
def test_audience_rejects_invalid_combinations(client, database, audience):
    response = client.post('/api/v1/knowledge/resources', json={'title': 'Guide', 'source_type': 'handbook', 'audience': audience})
    assert response.status_code == 422
    database.rpc.assert_not_called()


def test_patch_requires_and_forwards_revision_token(client, database):
    response = client.patch(f'/api/v1/knowledge/resources/{SOURCE}/revisions/{REVISION}',
        json={'expected_version': 4, 'title': 'Updated guide'})
    assert response.status_code == 200
    _, parameters = database.rpc.call_args.args
    assert parameters['expected_version'] == 4
    assert parameters['payload'] == {'title': 'Updated guide'}


def test_multipart_upload_reaches_upload_route_before_review_action(client, monkeypatch, revision):
    upload = AsyncMock(return_value={'revision': revision})
    monkeypatch.setattr(uploads, 'upload', upload)
    response = client.post(f'/api/v1/knowledge/revisions/{REVISION}/documents',
        data={'expected_version': '4'}, files={'file': ('guide.txt', b'Fictional guide', 'text/plain')})
    assert response.status_code == 201
    arguments = upload.call_args.args
    assert str(arguments[1]) == REVISION and arguments[2] == 4
    assert arguments[3].filename == 'guide.txt'
    assert 'storage_object_key' not in response.json()


def test_retry_index_reaches_retry_route_before_review_action(client, monkeypatch, revision):
    retry = MagicMock(return_value=revision)
    monkeypatch.setattr(uploads, 'retry_index', retry)
    response = client.post(f'/api/v1/knowledge/revisions/{REVISION}/retry-index',
        json={'expected_version': 4, 'document_version_id': VERSION})
    assert response.status_code == 200
    arguments = retry.call_args.args
    assert str(arguments[1]) == REVISION and arguments[2] == 4 and str(arguments[3]) == VERSION


@pytest.mark.parametrize(('code', 'status'), [('40001', 409), ('42501', 403), ('P0002', 404), ('PGRST202', 503)])
def test_database_denials_remain_safe_and_actionable(client, database, code, status):
    database.rpc.side_effect = DatabaseFailure(code)
    response = client.post(f'/api/v1/knowledge/revisions/{REVISION}/publish', json={'expected_version': 4, 'expected_policy': 0})
    assert response.status_code == status
    assert 'Private database detail' not in response.text


def test_publish_requires_live_policy_token(client, database):
    response = client.post(f'/api/v1/knowledge/revisions/{REVISION}/publish', json={'expected_version': 4})
    assert response.status_code == 422
    database.rpc.assert_not_called()


def test_read_does_not_accept_a_client_selected_tenant(client, database):
    response = client.get('/api/v1/knowledge/resources?institution_id=other-college')
    assert response.status_code == 200
    _, parameters = database.rpc.call_args.args
    assert parameters['tenant'] == TENANT
    assert 'storage_object_key' not in response.text


def test_resource_routes_require_authentication_without_overrides():
    from fastapi.testclient import TestClient
    from app.main import app

    response = TestClient(app, raise_server_exceptions=False).get('/api/v1/knowledge/resources')
    assert response.status_code == 401


@pytest.mark.parametrize(('permissions', 'mode'), [
    (['ai.knowledge.create'], 'own'),
    (['ai.knowledge.create', 'ai.knowledge.read'], 'review'),
])
def test_admin_own_draft_read_does_not_require_institution_review_access(client, database, user, permissions, mode):
    user['roles'] = ['admin']
    user['authorization_context'].role = 'admin'
    user['effective_permissions'] = permissions
    response = client.get(f'/api/v1/knowledge/revisions/{REVISION}')
    assert response.status_code == 200
    _, parameters = database.rpc.call_args.args
    assert parameters['mode'] == mode
