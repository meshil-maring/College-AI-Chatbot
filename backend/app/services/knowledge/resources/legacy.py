"""Keep old upload URLs while staging all new file content in private revisions."""

from app.schemas.knowledge.resources import DraftFields
from .operations import execute, identity, save_draft
from .uploads import upload


async def upload_source(user, source_id, file, *, document_id=None, version_label=None, auto_process=True):
    draft = save_draft(user, DraftFields(), source_id=source_id)
    result = await upload(user, draft['revision_id'], draft['revision_version'], file,
        document_id=document_id, version_label=version_label, auto_process=auto_process)
    version = next(item for item in result['revision']['documents']
        if str(item['document_version_id']) == str(result['document_version_id']))
    return {
        'knowledge_source_id': str(source_id), 'document_id': result['document_id'],
        'document_version_id': result['document_version_id'], 'processing_run_id': result['processing_run_id'],
        'storage_object_key': result['storage_object_key'],
        'version_number': version['version_number'], 'supersedes_version_id': None,
        'pipeline': result['pipeline'],
        'status': result['pipeline']['status'] if result['pipeline'] else 'queued',
        'revision_id': draft['revision_id'],
    }


def assert_delete(user, source_id):
    execute('assert_legacy_knowledge_delete', **identity(user), source_id=str(source_id))
