"""Staged upload validation, permission checks and uncertain commit recovery."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.errors import AppError
from app.services.knowledge.resources import uploads
from app.services.knowledge.resources import legacy
from .conftest import DOCUMENT, VERSION, REVISION


def file():
    return UploadFile(filename='guide.txt', file=BytesIO(b'Fictional learning material'),
        headers=Headers({'content-type': 'text/plain'}))


@pytest.fixture
def upload_io(monkeypatch, revision):
    monkeypatch.setattr(uploads, 'read_revision', lambda *_: revision)
    monkeypatch.setattr(uploads, 'get_r2_client', lambda: object())
    put, delete = MagicMock(), MagicMock()
    monkeypatch.setattr(uploads, 'upload_file', put)
    monkeypatch.setattr(uploads, 'delete_file', delete)
    return put, delete


@pytest.mark.asyncio
async def test_registers_draft_without_publishing_or_superseding(monkeypatch, user, revision, upload_io):
    execute = MagicMock(return_value={'document_id': DOCUMENT, 'document_version_id': VERSION,
        'processing_run_id': VERSION, 'revision': revision})
    monkeypatch.setattr(uploads, 'execute', execute)
    result = await uploads.upload(user, REVISION, 4, file(), auto_process=False)
    parameters = execute.call_args.kwargs
    assert parameters['expected_version'] == 4
    assert parameters['file_metadata']['file_checksum'].startswith('sha256:')
    assert 'lifecycle_status' not in parameters['file_metadata']
    assert result['revision']['lifecycle_status'] == 'draft'
    upload_io[1].assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(('status', 'cleanup'), [(403, True), (409, True), (500, False)])
async def test_cleanup_distinguishes_rejection_from_unknown_commit(monkeypatch, user, upload_io, status, cleanup):
    monkeypatch.setattr(uploads, 'execute', MagicMock(side_effect=AppError('Failed', status, 'TEST')))
    with pytest.raises(AppError):
        await uploads.upload(user, REVISION, 4, file(), auto_process=False)
    assert upload_io[1].called is cleanup


@pytest.mark.asyncio
async def test_revoked_upload_permission_stops_before_storage(user, upload_io):
    user['effective_permissions'] = ['ai.knowledge.create']
    with pytest.raises(AppError) as failure:
        await uploads.upload(user, REVISION, 4, file())
    assert failure.value.status_code == 403
    upload_io[0].assert_not_called()


@pytest.mark.asyncio
async def test_legacy_receipt_preserves_version_and_indexing_contract(monkeypatch, user, revision):
    revision['documents'] = [{'document_version_id': VERSION, 'version_number': 3}]
    monkeypatch.setattr(legacy, 'save_draft', lambda *_args, **_kwargs: revision)
    staged = AsyncMock(return_value={'document_id': DOCUMENT, 'document_version_id': VERSION,
        'processing_run_id': VERSION, 'storage_object_key': 'private/file.txt',
        'pipeline': {'status': 'embedded'}, 'revision': revision})
    monkeypatch.setattr(legacy, 'upload', staged)
    result = await legacy.upload_source(user, revision['knowledge_source_id'], file(),
        document_id=DOCUMENT, version_label='Third edition')
    assert result['version_number'] == 3 and result['status'] == 'embedded'
    assert result['revision_id'] == REVISION and result['supersedes_version_id'] is None
    assert staged.call_args.kwargs['version_label'] == 'Third edition'
