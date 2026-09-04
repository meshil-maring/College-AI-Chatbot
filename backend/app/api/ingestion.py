from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.errors import AppError
from app.core.security import require_roles
from app.db.supabase import get_admin_client
from app.repositories.ingestion import (
    get_processing_run_with_version,
    store_extracted_text,
    update_run_status,
)
from app.schemas.ingestion import ExtractionResponse, IngestResponse
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
    processing_run_id: str,
    current_user: dict = Depends(_INGEST_ALLOWED),
) -> ExtractionResponse:
    db = get_admin_client()
    run = get_processing_run_with_version(db, processing_run_id)

    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    if run["status"] != "queued":
        raise AppError(
            f"Run is not in queued state (current: {run['status']})",
            status_code=409,
            code="RUN_NOT_QUEUED",
        )

    dv = run["document_versions"]
    now = datetime.now(timezone.utc).isoformat()
    update_run_status(db, processing_run_id, status="processing", started_at=now)

    try:
        r2 = get_r2_client()
        data = download_file(r2, dv["storage_bucket"], dv["storage_object_key"])
        text = extract_text(data, dv["file_type"])
    except Exception as exc:
        completed = datetime.now(timezone.utc).isoformat()
        update_run_status(
            db,
            processing_run_id,
            status="failed",
            completed_at=completed,
            error_message=str(exc)[:1000],
        )
        raise AppError(str(exc), status_code=500, code="EXTRACTION_FAILED") from exc

    completed = datetime.now(timezone.utc).isoformat()
    store_extracted_text(db, dv["document_version_id"], text)
    update_run_status(db, processing_run_id, status="ready", completed_at=completed)

    return ExtractionResponse(
        processing_run_id=processing_run_id,
        document_version_id=dv["document_version_id"],
        status="ready",
        characters_extracted=len(text),
    )
