"""Stage validated files in private revisions without superseding live content."""

import hashlib
from uuid import uuid4

from app.config import settings
from app.core.errors import AppError
from app.core.security import authorize_permissions, has_permission
from app.services.admin.admin_documents import process_run_to_retrieval
from app.services.knowledge.ingestion import (
    _extension, _safe_filename, _validate, read_upload_limited, validate_file_content,
)
from app.services.knowledge.storage import delete_file, get_r2_client, upload_file
from .operations import execute, identity, revisions


def read_revision(user, revision_id):
    context = user.get('authorization_context')
    review = getattr(context, 'role', None) == 'admin' and has_permission(user, 'ai.knowledge.read')
    return revisions(user, revision_id=revision_id, review=review)['items'][0]


async def upload(user, revision_id, expected_version, file, *, document_id=None, version_label=None, auto_process=True):
    authorize_permissions(user, 'ai.knowledge.create', 'documents.update' if document_id else 'documents.create')
    draft = read_revision(user, revision_id)
    if draft['lifecycle_status'] != 'draft':
        raise AppError('Return the resource to draft before uploading.', 409, 'RESOURCE_CHANGED')
    data = await read_upload_limited(file)
    _validate(file.filename or '', file.content_type or '', len(data))
    validate_file_content(file.filename or '', data)
    context = identity(user)
    object_key = f"{context['tenant']}/{draft['knowledge_source_id']}/{uuid4()}/{_safe_filename(file.filename or '')}"
    storage = get_r2_client()
    upload_file(storage, settings.r2_bucket, object_key, data, file.content_type or '')
    try:
        registered = execute('register_knowledge_upload', **context, revision=str(revision_id),
            expected_version=expected_version, selected_document=str(document_id) if document_id else None,
            file_metadata={
                'original_filename': file.filename or '', 'file_type': _extension(file.filename or ''),
                'mime_type': file.content_type or '', 'file_size_bytes': len(data),
                'storage_bucket': settings.r2_bucket, 'storage_object_key': object_key,
                'file_checksum': f'sha256:{hashlib.sha256(data).hexdigest()}',
                'version_label': version_label,
            })
    except AppError as failure:
        # A definite rejected transaction cannot reference the file. An unknown
        # transport/commit outcome may have saved it; preserve that object.
        if failure.status_code in {403, 404, 409, 422, 503}:
            delete_file(storage, settings.r2_bucket, object_key)
        raise
    # Reuse the established extraction/chunk/embedding orchestration. It leaves
    # new versions in draft; publication is exclusively the review transaction.
    registered['pipeline'] = None
    if auto_process:
        try:
            registered['pipeline'] = process_run_to_retrieval(registered['processing_run_id'])
        except Exception as failure:
            raise AppError('The upload was saved, but indexing failed. Review the draft and retry indexing.',
                422, 'RESOURCE_INDEXING_FAILED') from failure
    registered['revision'] = read_revision(user, revision_id)
    registered['storage_object_key'] = object_key  # Internal/legacy upload receipt only.
    return registered


def retry_index(user, revision_id, expected_version, version_id):
    run_id = execute('retry_knowledge_index', **identity(user), revision=str(revision_id),
        expected_version=expected_version, version_id=str(version_id))
    try:
        process_run_to_retrieval(run_id)
    except Exception as failure:
        raise AppError('Indexing failed. The draft remains available for retry.', 422, 'RESOURCE_INDEXING_FAILED') from failure
    return read_revision(user, revision_id)
