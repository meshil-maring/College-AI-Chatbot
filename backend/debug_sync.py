"""Debug script for FAQ sync failure."""
import sys
sys.path.insert(0, '.')
from uuid import UUID, uuid4
import hashlib
import traceback

from app.db.supabase import get_admin_client
from app.services.storage import get_r2_client, upload_file
from app.services.admin_documents import (
    _get_or_create_canonical_knowledge_source,
    find_document_by_marker,
    sync_canonical_text_record,
)
from app.repositories.admin_knowledge import create_next_document_version
from app.repositories.ingestion import create_document, create_processing_run
from app.schemas.admin import DocumentVersionCreate
from app.config import settings


def main():
    db = get_admin_client()
    r2 = get_r2_client()

    institution_id = '30000000-0000-0000-0000-000000000001'
    source_type = 'faq'
    knowledge_source_title = 'Frequently Asked Questions'
    marker = 'faq:30000000-0000-0000-0000-000000000999'
    canonical_text = 'FAQ [academics] Test FAQ?\nTest answer.'
    actor_user_id = '30000000-0000-0000-0000-000000000001'

    print('Step 1: Get or create KS...')
    ks = _get_or_create_canonical_knowledge_source(
        db, institution_id, source_type, knowledge_source_title, actor_user_id
    )
    print(f'KS: {ks}')

    print('Step 2: Find document by marker...')
    document_id = find_document_by_marker(db, marker)
    print(f'Document ID: {document_id}')

    if document_id is None:
        print('Step 3: Create document...')
        document = create_document(db, ks['knowledge_source_id'])
        document_id = document['document_id']
        print(f'Created document: {document_id}')

    print('Step 4: Prepare data...')
    data = canonical_text.encode('utf-8')
    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    scope = str(institution_id) if institution_id is not None else 'global'
    object_key = f"{scope}/{ks['knowledge_source_id']}/{uuid4()}/{marker}.txt"
    print(f'Object key: {object_key}')

    print('Step 5: Upload to R2...')
    upload_file(r2, settings.r2_bucket, object_key, data, 'text/plain')
    print('Uploaded')

    print('Step 6: Create next document version...')
    version = create_next_document_version(
        db,
        DocumentVersionCreate(
            document_id=UUID(str(document_id)),
            original_filename=f'{marker}.txt',
            file_type='txt',
            mime_type='text/plain',
            file_size_bytes=len(data),
            storage_bucket=settings.r2_bucket,
            storage_object_key=object_key,
            file_checksum=checksum,
            version_label=marker,
        ),
        actor_user_id,
    )
    print(f'Version: {version}')

    print('Step 7: Create processing run...')
    run = create_processing_run(
        db,
        document_version_id=version['document_version_id'],
        processor_name=settings.app_name,
        processor_version=settings.app_version,
    )
    print(f'Run: {run}')

    print('\nAll steps succeeded — now testing full sync...')
    result = sync_canonical_text_record(
        institution_id=institution_id,
        source_type=source_type,
        knowledge_source_title=knowledge_source_title,
        marker=marker,
        canonical_text=canonical_text,
        actor_user_id=actor_user_id,
        client=db,
    )
    print(f'Sync result: {result}')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
