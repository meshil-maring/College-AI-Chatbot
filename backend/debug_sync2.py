"""Targeted debug: trace the exact failure in sync_canonical_text_record."""
import sys
sys.path.insert(0, '.')
from uuid import UUID, uuid4
import hashlib
import traceback
import httpx

from app.db.supabase import get_admin_client, create_supabase_client
from app.services.storage import get_r2_client, upload_file
from app.config import settings

from app.services.admin_documents import (
    _get_or_create_canonical_knowledge_source,
    find_document_by_marker,
    sync_canonical_text_record,
    purge_version_retrieval_content,
)
from app.repositories.ingestion import (
    create_document,
    create_processing_run,
)
from app.repositories.admin_knowledge import create_next_document_version
from app.schemas.admin import DocumentVersionCreate


def get_real_admin_token():
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': 'admin.demo@collegelocal.dev'})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': 'admin.demo@collegelocal.dev', 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token


def main():
    db = get_admin_client()
    r2 = get_r2_client()

    institution_id = '30000000-0000-0000-0000-000000000001'
    source_type = 'faq'
    knowledge_source_title = 'Frequently Asked Questions'
    marker = 'faq:30000000-0000-0000-0000-000000000999'
    canonical_text = 'FAQ [academics] Test FAQ?\nTest answer.'
    actor_user_id = '30000000-0000-0000-0000-000000000102'  # Real admin user ID

    print('Step 1: Get or create KS...')
    try:
        ks = _get_or_create_canonical_knowledge_source(
            db, institution_id, source_type, knowledge_source_title, actor_user_id
        )
        print(f'  KS: {ks["knowledge_source_id"]}')
    except Exception as e:
        print(f'  FAILED: {e}')
        import traceback; traceback.print_exc()
        return

    print('Step 2: Find document by marker...')
    document_id = find_document_by_marker(db, marker)
    print(f'  Document ID: {document_id}')

    if document_id is None:
        print('Step 3: Create document...')
        document = create_document(db, ks['knowledge_source_id'])
        document_id = document['document_id']
        print(f'  Created document: {document_id}')
    else:
        print('Step 3: Purge old versions...')
        previous = __import__('app.services.admin_documents', fromlist=['get_document_with_versions']).get_document_with_versions(db, document_id)
        old_version_ids = [v['document_version_id'] for v in (previous.get('versions') or [])]
        print(f'  Old version IDs: {old_version_ids}')
        purge_version_retrieval_content(db, old_version_ids)
        print('  Purged')

    print('Step 4: Prepare data...')
    data = canonical_text.encode('utf-8')
    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    scope = str(institution_id)
    object_key = f"{scope}/{ks['knowledge_source_id']}/{uuid4()}/{marker}.txt"
    print(f'  Object key: {object_key}')

    print('Step 5: Upload to R2...')
    upload_file(r2, settings.r2_bucket, object_key, data, 'text/plain')
    print('  Uploaded')

    print('Step 6: Create next document version...')
    try:
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
        print(f'  Version: {version["document_version_id"]}')
    except Exception as e:
        print(f'  Version creation FAILED: {e}')
        traceback.print_exc()
        return

    print('Step 7: Create processing run...')
    try:
        run = create_processing_run(
            db,
            document_version_id=version['document_version_id'],
            processor_name=settings.app_name,
            processor_version=settings.app_version,
        )
        print(f'  Run: {run["processing_run_id"]}')
    except Exception as e:
        print(f'  Run creation FAILED: {e}')
        traceback.print_exc()
        return

    print('Step 8: Process run to retrieval...')
    try:
        from app.services.admin_documents import process_run_to_retrieval
        pipeline = process_run_to_retrieval(run['processing_run_id'], db)
        print(f'  Pipeline: status={pipeline["status"]}, chunks={pipeline["chunks_created"]}, embeddings={pipeline["embeddings_created"]}')
    except Exception as e:
        print(f'  Pipeline FAILED: {e}')
        traceback.print_exc()
        return

    print('Step 9: Update lifecycle to published...')
    try:
        from app.repositories.admin_knowledge import update_document_version_lifecycle
        update_document_version_lifecycle(db, version['document_version_id'], 'published')
        print('  Done')
    except Exception as e:
        print(f'  Lifecycle update FAILED: {e}')
        traceback.print_exc()
        return

    print('\n=== ALL STEPS SUCCEEDED ===')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
