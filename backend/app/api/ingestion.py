import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.errors import AppError
from app.core.security import (
    assert_tenant_object,
    require_institution_roles,
    require_permission,
)
from app.db.supabase import get_admin_client
from app.repositories import admin_knowledge as knowledge_repo
from app.repositories.ingestion import (
    get_knowledge_source,
    get_processing_run_with_version,
    store_extracted_text,
    update_run_status,
    get_extracted_text,
    delete_chunks_for_run,
    insert_chunks,
)
from app.schemas.ingestion import (
    ChunkingResponse,
    EmbeddingResponse,
    ExtractionResponse,
    IngestResponse,
)
from app.services.chunking import chunk_text
from app.services.embeddings import embed_processing_run
from app.services.extraction import extract_text
from app.services.ingestion import ingest_document
from app.services.storage import download_file, get_r2_client

router = APIRouter(prefix="/documents", tags=["documents"])

logger = logging.getLogger(__name__)

_INGEST_ALLOWED = require_institution_roles("admin", "staff", "faculty")


def _assert_source_tenant(current_user: dict, source: dict | None) -> None:
    """Require an institution-owned source inside the resolved caller scope."""
    if source is None:
        raise AppError(
            "Knowledge source not found", 404, "KNOWLEDGE_SOURCE_NOT_FOUND"
        )
    # The shared helper permits global rows. Processing requires an owner,
    # and the institution dependency pins the caller to an active grant.
    if not source.get("institution_id") or not current_user.get("institution_id"):
        raise AppError(
            "This resource does not belong to your institution", 403, "TENANT_MISMATCH"
        )
    assert_tenant_object(current_user, source["institution_id"])


def _assert_run_tenant(
    current_user: dict,
    run: dict | None,
    db,
) -> None:
    """Resolve run -> version -> document -> source and fail closed.

    The repository hoists documents.knowledge_source_id onto the version
    projection. An unresolved relationship never authorizes processing.
    """
    if run is None:
        raise AppError("Processing run not found", 404, "RUN_NOT_FOUND")
    dv = run.get("document_versions") or {}
    ks_id = dv.get("knowledge_source_id") if isinstance(dv, dict) else None
    if not ks_id:
        raise AppError(
            "Knowledge source not found", 404, "KNOWLEDGE_SOURCE_NOT_FOUND"
        )
    ks = knowledge_repo.get_knowledge_source_detail(db, ks_id)
    _assert_source_tenant(current_user, ks)


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(
    file: UploadFile,
    knowledge_source_id: str = Form(...),
    current_user: dict = Depends(_INGEST_ALLOWED),
    _permission_user: dict = Depends(require_permission("ai.knowledge.create")),
) -> IngestResponse:
    if not knowledge_source_id.strip():
        raise AppError(
            "Knowledge source not found", 404, "KNOWLEDGE_SOURCE_NOT_FOUND"
        )
    ks = get_knowledge_source(get_admin_client(), knowledge_source_id)
    _assert_source_tenant(current_user, ks)
    return await ingest_document(
        file=file,
        knowledge_source_id=knowledge_source_id,
        user_id=current_user["user_id"],
    )


@router.post("/{processing_run_id}/extract", response_model=ExtractionResponse)
def extract(
    processing_run_id: UUID,
    current_user: dict = Depends(_INGEST_ALLOWED),
    _permission_user: dict = Depends(require_permission("ai.knowledge.create")),
) -> ExtractionResponse:
    db = get_admin_client()
    run = get_processing_run_with_version(db, str(processing_run_id))

    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    _assert_run_tenant(current_user, run, db)
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
        # Phase 6.21 — production hardening: the DB row keeps the raw detail
        # for operators; the API response stays a fixed safe message so file
        # contents, SQL text, and storage internals can never leak to clients.
        logger.exception("Document extraction failed (run_id=%s)", run_id_str)
        raise AppError(
            "Document processing failed during extraction",
            status_code=500,
            code="EXTRACTION_FAILED",
        ) from exc

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
    _permission_user: dict = Depends(require_permission("ai.knowledge.create")),
) -> ChunkingResponse:
    db = get_admin_client()
    run_id_str = str(processing_run_id)
    run = get_processing_run_with_version(db, run_id_str)

    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    _assert_run_tenant(current_user, run, db)
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
        # Phase 6.21 — production hardening: the DB row keeps the raw detail
        # for operators; the API response stays a fixed safe message.
        logger.exception("Document chunking failed (run_id=%s)", run_id_str)
        raise AppError(
            "Document processing failed during chunking",
            status_code=500,
            code="CHUNKING_FAILED",
        ) from exc

    return ChunkingResponse(
        processing_run_id=run_id_str,
        document_version_id=document_version_id,
        status="ready",
        chunks_created=len(chunks),
    )


@router.post("/{processing_run_id}/embed", response_model=EmbeddingResponse)
def embed(
    processing_run_id: UUID,
    current_user: dict = Depends(_INGEST_ALLOWED),
    _permission_user: dict = Depends(require_permission("ai.knowledge.create")),
) -> EmbeddingResponse:
    run_id_str = str(processing_run_id)
    db = get_admin_client()
    run = get_processing_run_with_version(db, run_id_str)
    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    # Phase 6.13.7: the run must belong to the caller's tenant (server-side).
    _assert_run_tenant(current_user, run, db)
    embeddings_created = embed_processing_run(run_id_str)
    return EmbeddingResponse(
        processing_run_id=run_id_str,
        status="embedded",
        embeddings_created=embeddings_created,
    )
