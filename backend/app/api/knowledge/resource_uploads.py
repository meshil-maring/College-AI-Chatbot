"""Private draft upload and indexing retry; publication is a separate command."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.security import require_institution_roles
from app.schemas.knowledge.resources import RevisionItem, RetryIndex
from app.services.knowledge.resources import uploads

router = APIRouter(prefix='/knowledge/revisions', tags=['learning-resources'])
_WRITE = require_institution_roles('admin', 'faculty', 'staff')


@router.post('/{revision_id}/documents', response_model=RevisionItem, status_code=201)
async def upload_document(revision_id: UUID, file: UploadFile,
                          expected_version: int = Form(..., ge=1), document_id: UUID | None = Form(None),
                          user: dict = Depends(_WRITE)):
    result = await uploads.upload(user, revision_id, expected_version, file, document_id=document_id)
    return result['revision']


@router.post('/{revision_id}/retry-index', response_model=RevisionItem)
def retry_index(revision_id: UUID, payload: RetryIndex, user: dict = Depends(_WRITE)):
    return uploads.retry_index(user, revision_id, payload.expected_version, payload.document_version_id)
