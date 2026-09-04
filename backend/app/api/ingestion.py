from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.errors import AppError
from app.core.security import require_roles
from app.db.supabase import get_admin_client
from app.repositories.ingestion import (
    get_processing_run_with_version,
    store_extracted_text,
    update_run_status,
    get_extracted_text,
    delete_chunks_for_run,
    insert_chunks,
)
from app.schemas.ingestion import ChunkingResponse, ExtractionResponse, IngestResponse
from app.services.chunking import chunk_text
from app.services.extraction import extract_text
from app.services.ingestion import ingest_document
from app.services.storage import download_file, get_r2_client

router = APIRouter(prefix="/documents", tags=["documents"])

_INGEST_ALLOWED = require_roles("admin", "staff", "faculty")


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(
    file: UploadFile,
    knowledge_source_id: str = Form(...),
    current_user: dict = Depends(_INGEST_ALLOWED),
) -> IngestResponse:
    return await ingest_document(
        file=file,
        knowledge_source_id=knowledge_source_id,
        user_id=current_user["user_id"],
    )


@router.post("/{processing_run_id}/extract", response_model=ExtractionResponse)
def extract(
    processing_run_id: UUID,
    current_user: dict = Depends(_INGEST_ALLOWED),
) -> ExtractionResponse:
    db = get_admin_client()
    run = get_processing_run_with_version(db, str(processing_run_id))

    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    if run["status"] != "queued":
        raise AppError(
            f"Run is not in queued state (current: {run['status']})",
            status_code=409,
            code="RUN_NOT_QUEUED",
        )

    dv = run["document_versions"]
    run_id_str = str(processing_run_id)
    now = datetime.now(timezone.utc).isoformat()
    update_run_status(db, run_id_str, status="processing", started_at=now)

    try:
        r2 = get_r2_client()
        data = download_file(r2, dv["storage_bucket"], dv["storage_object_key"])
        text = extract_text(data, dv["file_type"])
    except Exception as exc:
        completed = datetime.now(timezone.utc).isoformat()
        update_run_status(
            db,
            run_id_str,
            status="failed",
            completed_at=completed,
            error_message=str(exc)[:1000],
        )
        raise AppError(str(exc), status_code=500, code="EXTRACTION_FAILED") from exc

    completed = datetime.now(timezone.utc).isoformat()
    store_extracted_text(db, dv["document_version_id"], text)
    update_run_status(db, run_id_str, status="ready", completed_at=completed)

    return ExtractionResponse(
        processing_run_id=run_id_str,
        document_version_id=dv["document_version_id"],
        status="ready",
        characters_extracted=len(text),
    )


@router.post("/{processing_run_id}/chunk", response_model=ChunkingResponse)
def chunk(
    processing_run_id: UUID,
    current_user: dict = Depends(_INGEST_ALLOWED),
) -> ChunkingResponse:
    db = get_admin_client()
    run_id_str = str(processing_run_id)
    run = get_processing_run_with_version(db, run_id_str)

    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    if run["status"] != "ready":
        raise AppError(
            f"Run is not in ready state (current: {run['status']})",
            status_code=409,
            code="RUN_NOT_READY",
        )

    dv = run["document_versions"]
    document_version_id = dv["document_version_id"]

    extracted_text = get_extracted_text(db, document_version_id) or ""

    try:
        delete_chunks_for_run(db, run_id_str)
        chunks = chunk_text(extracted_text)
        if chunks:
            insert_chunks(db, run_id_str, chunks)
    except Exception as exc:
        delete_chunks_for_run(db, run_id_str)
        update_run_status(
            db,
            run_id_str,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=str(exc)[:1000],
        )
        raise AppError(str(exc), status_code=500, code="CHUNKING_FAILED") from exc

    return ChunkingResponse(
        processing_run_id=run_id_str,
        document_version_id=document_version_id,
        status="ready",
        chunks_created=len(chunks),
    )
