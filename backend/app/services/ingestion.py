import hashlib
import uuid

from fastapi import UploadFile

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.ingestion import (
    create_document,
    create_document_version,
    create_processing_run,
    get_knowledge_source,
)
from app.schemas.ingestion import IngestResponse
from app.services.storage import delete_file, get_r2_client, upload_file

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _validate(filename: str, content_type: str, size: int) -> None:
    if size == 0:
        raise AppError("File is empty", status_code=422, code="EMPTY_FILE")
    if _extension(filename) not in ALLOWED_EXTENSIONS:
        raise AppError(
            f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            status_code=422,
            code="INVALID_FILE_TYPE",
        )
    if content_type not in ALLOWED_MIME_TYPES:
        raise AppError(
            f"Unsupported MIME type: {content_type}",
            status_code=422,
            code="INVALID_MIME_TYPE",
        )
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size > max_bytes:
        raise AppError(
            f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
            status_code=413,
            code="FILE_TOO_LARGE",
        )


async def ingest_document(
    file: UploadFile,
    knowledge_source_id: str,
    user_id: str,
) -> IngestResponse:
    data = await file.read()

    _validate(file.filename or "", file.content_type or "", len(data))

    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    ext = _extension(file.filename or "")
    db = get_admin_client()

    ks = get_knowledge_source(db, knowledge_source_id)
    if ks is None:
        raise AppError(
            f"Knowledge source '{knowledge_source_id}' not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )

    doc = create_document(db, knowledge_source_id)
    doc_id = doc["document_id"]

    version_uuid = str(uuid.uuid4())
    object_key = f"{ks['institution_id']}/{knowledge_source_id}/{version_uuid}/{file.filename}"

    r2 = get_r2_client()
    upload_file(r2, settings.r2_bucket, object_key, data, file.content_type or "")

    try:
        dv = create_document_version(
            db,
            document_id=doc_id,
            user_id=user_id,
            original_filename=file.filename or "",
            file_type=ext,
            mime_type=file.content_type or "",
            file_size_bytes=len(data),
            storage_bucket=settings.r2_bucket,
            storage_object_key=object_key,
            file_checksum=checksum,
        )
        dv_id = dv["document_version_id"]

        run = create_processing_run(
            db,
            document_version_id=dv_id,
            processor_name=settings.app_name,
            processor_version=settings.app_version,
        )
    except Exception as exc:
        delete_file(r2, settings.r2_bucket, object_key)
        raise AppError(
            "Database registration failed; storage upload has been rolled back.",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    return IngestResponse(
        knowledge_source_id=knowledge_source_id,
        document_id=doc_id,
        document_version_id=dv_id,
        processing_run_id=run["processing_run_id"],
        storage_object_key=object_key,
        status="queued",
    )
