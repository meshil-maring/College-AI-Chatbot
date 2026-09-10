"""Admin document orchestration services (Phase Admin-3).

Wraps the existing, locked RAG pipeline (upload → extraction → chunking →
embedding → retrieval) for the Admin API WITHOUT modifying it:

  * new documents are ingested through ``app.services.ingestion.ingest_document``
  * updated documents register a new revision through the Admin-2 helper
    ``create_next_document_version`` (the existing ``create_document_version``
    implementation in ``app.repositories.ingestion`` is untouched)
  * pipeline execution reuses the existing extraction / chunking / embedding
    services and repositories
  * updates and deletes purge stale retrieval content (chunks + embeddings)
    so superseded versions never remain retrievable

This module also hosts the shared canonical-text synchronization engine used
by the FAQ and notice services — the database record is the source of truth
and its rendered text is stored/synced through the existing
document/version/processing pipeline while preserving institution scope.
"""

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import UploadFile
from supabase import Client

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin_knowledge import (
    create_next_document_version,
    get_document_with_versions,
    update_document_version_lifecycle,
)
from app.repositories.embeddings import delete_embeddings_for_run
from app.repositories.ingestion import (
    create_document,
    create_processing_run,
    delete_chunks_for_run,
    get_processing_run_with_version,
    insert_chunks,
    store_extracted_text,
    update_run_status,
)
from app.schemas.admin import DocumentVersionCreate
from app.services.chunking import chunk_text
from app.services.embeddings import embed_processing_run
from app.services.extraction import extract_text
from app.services.ingestion import _extension, _validate, ingest_document
from app.services.storage import (
    delete_file,
    download_file,
    get_r2_client,
    upload_file,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# Pipeline execution (reuses the existing locked RAG services/repositories)
# ============================================================================


def process_run_to_retrieval(
    processing_run_id: str,
    client: Client | None = None,
) -> dict:
    """Drive one queued processing run through the full RAG pipeline.

    Runs the existing extraction → chunking → embedding steps against the
    already-registered processing run created by ``ingest_document`` (or
    ``create_processing_run``). The RAG implementation itself is not modified;
    this only orchestrates the existing building blocks in sequence.
    """
    db = client or get_admin_client()
    run_id = str(processing_run_id)

    run = get_processing_run_with_version(db, run_id)
    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")
    if run["status"] != "queued":
        raise AppError(
            f"Run is not in queued state (current: {run['status']})",
            status_code=409,
            code="RUN_NOT_QUEUED",
        )

    dv = run["document_versions"]
    document_version_id = dv["document_version_id"]

    # --- extraction (existing services/repositories) -----------------------
    update_run_status(db, run_id, status="processing", started_at=_utc_now())
    try:
        r2 = get_r2_client()
        data = download_file(r2, dv["storage_bucket"], dv["storage_object_key"])
        text = extract_text(data, dv["file_type"])
    except Exception as exc:
        update_run_status(
            db,
            run_id,
            status="failed",
            completed_at=_utc_now(),
            error_message=str(exc)[:1000],
        )
        raise AppError(
            "Document processing failed during extraction",
            status_code=500,
            code="EXTRACTION_FAILED",
        ) from exc

    store_extracted_text(db, document_version_id, text)
    update_run_status(db, run_id, status="ready", completed_at=_utc_now())

    # --- chunking (existing services/repositories) --------------------------
    try:
        delete_chunks_for_run(db, run_id)
        chunks = chunk_text(text or "")
        if chunks:
            insert_chunks(db, run_id, chunks)
    except Exception as exc:
        delete_chunks_for_run(db, run_id)
        update_run_status(
            db,
            run_id,
            status="failed",
            completed_at=_utc_now(),
            error_message=str(exc)[:1000],
        )
        raise AppError(
            "Document processing failed during chunking",
            status_code=500,
            code="CHUNKING_FAILED",
        ) from exc

    # --- embedding (existing locked service) --------------------------------
    embeddings_created = embed_processing_run(run_id)

    return {
        "processing_run_id": run_id,
        "document_version_id": document_version_id,
        "status": "embedded",
        "characters_extracted": len(text or ""),
        "chunks_created": len(chunks),
        "embeddings_created": embeddings_created,
    }

# ============================================================================
# Stale retrieval-content management
# ============================================================================


def list_run_ids_for_versions(client: Client, document_version_ids: list[str]) -> list[str]:
    """Return the processing-run ids registered for the given versions."""
    run_ids: list[str] = []
    for version_id in document_version_ids:
        response = (
            client.table("document_processing_runs")
            .select("processing_run_id")
            .eq("document_version_id", str(version_id))
            .execute()
        )
        run_ids.extend(row["processing_run_id"] for row in (response.data or []))
    return run_ids


def purge_version_retrieval_content(
    client: Client,
    document_version_ids: list[str],
) -> list[str]:
    """Remove chunks, embeddings, and processing runs for the given versions.

    This guarantees that superseded/archived/deleted document versions never
    leave stale retrievable content behind.
    """
    if not document_version_ids:
        return []

    run_ids = list_run_ids_for_versions(client, document_version_ids)
    for run_id in run_ids:
        chunk_rows = (
            client.table("knowledge_chunks")
            .select("chunk_id")
            .eq("processing_run_id", run_id)
            .execute()
            .data
            or []
        )
        chunk_ids = [row["chunk_id"] for row in chunk_rows if row.get("chunk_id")]
        if chunk_ids:
            client.table("message_citations").delete().in_(
                "chunk_id", chunk_ids
            ).execute()
            client.table("retrieved_chunks").delete().in_(
                "chunk_id", chunk_ids
            ).execute()
        delete_embeddings_for_run(client, run_id, settings.embedding_model)
        delete_chunks_for_run(client, run_id)
    if run_ids:
        client.table("document_processing_runs").delete().in_(
            "processing_run_id", run_ids
        ).execute()
    return run_ids


# ============================================================================
# Upload / update / delete
# ============================================================================


async def upload_document(
    file: UploadFile,
    knowledge_source_id: str,
    user_id: str,
    auto_process: bool = True,
) -> dict:
    """Upload a new document into an existing knowledge source.

    Reuses the existing locked ``ingest_document`` flow (storage upload →
    document + version-1 + queued processing run) and, when ``auto_process``
    is set, drives the queued run through the full RAG pipeline immediately.
    """
    result = await ingest_document(
        file=file,
        knowledge_source_id=knowledge_source_id,
        user_id=user_id,
    )
    payload = result.model_dump()
    if auto_process:
        payload["pipeline"] = process_run_to_retrieval(result.processing_run_id)
    return payload

async def update_document(
    file: UploadFile,
    document_id: UUID | str,
    user_id: str,
    version_label: str | None = None,
    auto_process: bool = True,
) -> dict:
    """Upload a new revision of an existing document.

    Uses the Admin-2 ``create_next_document_version`` helper (the previous
    latest version is superseded and marked as such). The superseded versions'
    chunks/embeddings are purged so stale retrieval content is removed.
    """
    data = await file.read()
    _validate(file.filename or "", file.content_type or "", len(data))

    db = get_admin_client()
    doc = get_document_with_versions(db, str(document_id))
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")

    # Purge retrieval content of all existing (about-to-be-superseded) versions.
    old_version_ids = [v["document_version_id"] for v in (doc.get("versions") or [])]
    purge_version_retrieval_content(db, old_version_ids)

    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    ext = _extension(file.filename or "")
    object_key = f"documents/{document_id}/{uuid4()}/{file.filename}"

    r2 = get_r2_client()
    upload_file(r2, settings.r2_bucket, object_key, data, file.content_type or "")

    try:
        version = create_next_document_version(
            db,
            DocumentVersionCreate(
                document_id=UUID(str(document_id)),
                original_filename=file.filename or "",
                file_type=ext,
                mime_type=file.content_type,
                file_size_bytes=len(data),
                storage_bucket=settings.r2_bucket,
                storage_object_key=object_key,
                file_checksum=checksum,
                version_label=version_label,
            ),
            user_id,
        )
        run = create_processing_run(
            db,
            document_version_id=version["document_version_id"],
            processor_name=settings.app_name,
            processor_version=settings.app_version,
        )
    except AppError:
        delete_file(r2, settings.r2_bucket, object_key)
        raise
    except Exception as exc:
        delete_file(r2, settings.r2_bucket, object_key)
        raise AppError(
            "New document version registration failed",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    pipeline = None
    if auto_process:
        pipeline = process_run_to_retrieval(run["processing_run_id"], db)
        update_document_version_lifecycle(db, version["document_version_id"], "published")

    return {
        "document_id": str(document_id),
        "document_version_id": version["document_version_id"],
        "version_number": version["version_number"],
        "supersedes_version_id": version.get("supersedes_version_id"),
        "processing_run_id": run["processing_run_id"],
        "storage_object_key": object_key,
        "pipeline": pipeline,
        "status": pipeline["status"] if pipeline else "queued",
    }

def delete_document(document_id: UUID | str, client: Client | None = None) -> dict:
    """Delete a document and all of its retrieval content.

    Chunks, embeddings, processing runs, and versions are removed so no stale
    content remains retrievable; storage objects are deleted best-effort.
    """
    db = client or get_admin_client()
    doc = get_document_with_versions(db, str(document_id))
    if doc is None:
        raise AppError("Document not found", status_code=404, code="DOCUMENT_NOT_FOUND")
    version_ids: list[str] = []
    storage_objects: dict[str, tuple[str, str]] = {}
    doc_versions = doc.get("versions") or doc.get("document_versions") or []
    if doc_versions:
        version_ids = [v["document_version_id"] for v in doc_versions]
        storage_objects = {
            v["document_version_id"]: (
                v.get("storage_bucket", ""),
                v.get("storage_object_key", ""),
            )
            for v in doc_versions
        }
        purge_version_retrieval_content(db, version_ids)
    # Also purge any processing runs for versions we may not have seen,
    # then delete versions directly by document_id (FK-safe; runs already gone).
    unseen: list[str] = []
    all_version_ids: list[str] = list(version_ids)
    if not all_version_ids:
        # No version metadata was returned; find versions and runs before deletion.
        response = (
            db.table("document_versions")
            .select("document_version_id, storage_bucket, storage_object_key")
            .eq("document_id", str(document_id))
            .execute()
        )
        rows = response.data or []
        all_version_ids = [row["document_version_id"] for row in rows]
        storage_objects = {
            row["document_version_id"]: (
                row.get("storage_bucket", ""),
                row.get("storage_object_key", ""),
            )
            for row in rows
        }
        if all_version_ids:
            unseen = list_run_ids_for_versions(db, all_version_ids)
            purge_version_retrieval_content(db, all_version_ids)
    if unseen:
        purge_version_retrieval_content(db, [vid for vid in unseen if vid not in set(all_version_ids)])
    db.table("document_versions").delete().eq("document_id", str(document_id)).execute()
    db.table("documents").delete().eq("document_id", str(document_id)).execute()
    r2 = get_r2_client()
    for vid in all_version_ids:
        bucket, object_key = storage_objects.get(vid, ("", ""))
        if bucket and object_key:
            delete_file(r2, bucket, object_key)
    return {"deleted": True, "document_id": str(document_id)}

# ============================================================================
# Canonical-text synchronization engine (FAQ / notice RAG sync)
# ============================================================================
# A FAQ/notice record is the source of truth. Its rendered canonical text is
# stored as a .txt document inside a dedicated knowledge source for the
# record's institution scope and pushed through the existing document /
# version / processing pipeline. The FAQ/notice id is recorded in the
# document version's ``version_label`` field (e.g. "faq:<uuid>") which is
# used to locate and supersede the synthetic document on later updates.


def _get_or_create_canonical_knowledge_source(
    client: Client,
    institution_id: UUID | str | None,
    source_type: str,
    title: str,
    actor_user_id: UUID | str,
) -> dict:
    """Return the dedicated knowledge source for a canonical-text category."""
    query = (
        client.table("knowledge_sources")
        .select("knowledge_source_id, institution_id, source_type, title")
        .eq("source_type", source_type)
    )
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    else:
        query = query.is_("institution_id", "null")
    existing = query.maybe_single().execute()
    if existing is not None and existing.data is not None:
        return existing.data

    row: dict = {
        "source_type": source_type,
        "title": title,
        "authority_level": "official",
        "lifecycle_status": "published",
        "created_by_user_id": str(actor_user_id),
    }
    if institution_id is not None:
        row["institution_id"] = str(institution_id)
    created = client.table("knowledge_sources").insert(row).execute()
    return created.data[0]


def find_document_by_marker(client: Client, marker: str) -> str | None:
    """Return the document id tagged with the given version-label marker."""
    response = (
        client.table("document_versions")
        .select("document_id")
        .eq("version_label", marker)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]["document_id"]

def sync_canonical_text_record(
    institution_id: UUID | str | None,
    source_type: str,
    knowledge_source_title: str,
    marker: str,
    canonical_text: str,
    actor_user_id: UUID | str,
    client: Client | None = None,
) -> dict:
    """Store/sync a canonical-text record through the RAG pipeline.

    Creates (or supersedes) the synthetic document tagged with ``marker``,
    uploads the rendered text, and runs the existing pipeline so the current
    content is the only retrievable content for the record. Institution scope
    is preserved via the dedicated knowledge source.
    """
    db = client or get_admin_client()

    ks = _get_or_create_canonical_knowledge_source(
        db, institution_id, source_type, knowledge_source_title, actor_user_id
    )

    document_id = find_document_by_marker(db, marker)
    if document_id is None:
        document = create_document(db, ks["knowledge_source_id"])
        document_id = document["document_id"]
    else:
        # Remove stale retrieval content of the previous synthetic versions.
        previous = get_document_with_versions(db, document_id)
        old_version_ids = [
            v["document_version_id"] for v in (previous.get("versions") or [])
        ]
        purge_version_retrieval_content(db, old_version_ids)

    data = canonical_text.encode("utf-8")
    checksum = f"sha256:{hashlib.sha256(data).hexdigest()}"
    scope = str(institution_id) if institution_id is not None else "global"
    object_key = f"{scope}/{ks['knowledge_source_id']}/{uuid4()}/{marker}.txt"

    r2 = get_r2_client()
    upload_file(r2, settings.r2_bucket, object_key, data, "text/plain")

    try:
        version = create_next_document_version(
            db,
            DocumentVersionCreate(
                document_id=UUID(str(document_id)),
                original_filename=f"{marker}.txt",
                file_type="txt",
                mime_type="text/plain",
                file_size_bytes=len(data),
                storage_bucket=settings.r2_bucket,
                storage_object_key=object_key,
                file_checksum=checksum,
                version_label=marker,
            ),
            actor_user_id,
        )
        run = create_processing_run(
            db,
            document_version_id=version["document_version_id"],
            processor_name=settings.app_name,
            processor_version=settings.app_version,
        )
    except AppError:
        delete_file(r2, settings.r2_bucket, object_key)
        raise
    except Exception as exc:
        delete_file(r2, settings.r2_bucket, object_key)
        raise AppError(
            "Canonical-text version registration failed",
            status_code=500,
            code="RAG_SYNC_FAILED",
        ) from exc

    pipeline = process_run_to_retrieval(run["processing_run_id"], db)
    update_document_version_lifecycle(db, version["document_version_id"], "published")

    return {
        "knowledge_source_id": ks["knowledge_source_id"],
        "document_id": document_id,
        "document_version_id": version["document_version_id"],
        "processing_run_id": run["processing_run_id"],
        "chunks_created": pipeline["chunks_created"],
        "status": "synced",
    }

def remove_canonical_text_record(
    marker: str,
    client: Client | None = None,
) -> bool:
    """Remove the synthetic document for a marker (delete/archive path).

    The document, its versions, and all retrieval content are removed so no
    stale content remains retrievable. Returns True when a document existed.
    """
    db = client or get_admin_client()
    document_id = find_document_by_marker(db, marker)
    if document_id is None:
        return False
    delete_document(document_id, client=db)
    return True

