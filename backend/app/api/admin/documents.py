"""Admin documents endpoints."""

from uuid import UUID

from fastapi import Depends, Form, UploadFile

from app.core.errors import AppError
from app.repositories.admin import admin_knowledge as knowledge_repo
from app.services.admin import admin_documents
from app.services.knowledge.resources import legacy as revision_uploads
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.get("/knowledge-sources/{knowledge_source_id}/documents")
def list_documents(
    knowledge_source_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    db = common.get_admin_client()
    ks = knowledge_repo.get_knowledge_source_detail(db, knowledge_source_id)
    if ks is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, ks.get("institution_id"))
    return knowledge_repo.list_documents_for_source(db, knowledge_source_id)


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = common.get_admin_client()
    doc = knowledge_repo.get_document_with_versions(db, document_id)
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")
    ks = knowledge_repo.get_knowledge_source_detail(db, doc["knowledge_source_id"])
    if ks is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, ks.get("institution_id"))
    return doc


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile,
    knowledge_source_id: UUID = Form(...),
    auto_process: bool = Form(default=True),
    current_user: dict = Depends(_ADMIN),
) -> dict:
    """Admin upload → ingestion → extraction → chunking → embedding → retrieval."""
    db = common.get_admin_client()
    ks = knowledge_repo.get_knowledge_source_detail(db, knowledge_source_id)
    if ks is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, ks.get("institution_id"))
    result = await revision_uploads.upload_source(current_user, knowledge_source_id, file, auto_process=auto_process)
    common.record_audit(
        current_user,
        "document.upload",
        "documents",
        result["document_id"],
        {
            "knowledge_source_id": str(knowledge_source_id),
            "auto_process": auto_process,
            "original_filename": file.filename,
        },
    )
    return result


@router.post("/documents/{document_id}/versions", status_code=201)
async def upload_document_version(
    document_id: UUID,
    file: UploadFile,
    version_label: str | None = Form(default=None),
    auto_process: bool = Form(default=True),
    current_user: dict = Depends(_ADMIN),
) -> dict:
    """Stage a replacement in a draft while the published version stays live."""
    db = common.get_admin_client()
    doc = knowledge_repo.get_document_with_versions(db, document_id)
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")
    ks = knowledge_repo.get_knowledge_source_detail(db, doc["knowledge_source_id"])
    if ks is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, ks.get("institution_id"))
    result = await revision_uploads.upload_source(current_user, doc['knowledge_source_id'], file,
        document_id=document_id, version_label=version_label, auto_process=auto_process)
    common.record_audit(
        current_user,
        "document.update",
        "documents",
        str(document_id),
        {
            "document_version_id": result["document_version_id"],
            "auto_process": auto_process,
            "original_filename": file.filename,
        },
    )
    return result


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = common.get_admin_client()
    doc = knowledge_repo.get_document_with_versions(db, document_id)
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")
    ks = knowledge_repo.get_knowledge_source_detail(db, doc["knowledge_source_id"])
    if ks is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, ks.get("institution_id"))
    revision_uploads.assert_delete(current_user, doc['knowledge_source_id'])
    result = admin_documents.delete_document(document_id)
    common.record_audit(
        current_user,
        "document.delete",
        "documents",
        str(document_id),
        None,
    )
    return result
