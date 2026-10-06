import hashlib
import io
import logging
import re
import uuid
import zipfile

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
MIME_TYPE_BY_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}

logger = logging.getLogger(__name__)


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _safe_filename(filename: str) -> str:
    """Return a storage-safe leaf filename derived from a client filename.

    Phase 6.21 — production hardening: the client filename is untrusted
    metadata. Directory components (``../../``), separators, and control
    characters must never reach the R2 object key; only the final path
    component survives, restricted to a conservative allowlist. The original
    filename is still stored verbatim in ``original_filename`` for display.
    """
    leaf = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    leaf = re.sub(r"[^A-Za-z0-9._-]+", "_", leaf).strip("._") or "upload"
    return leaf[:128]


def _validate(filename: str, content_type: str, size: int) -> None:
    if size == 0:
        raise AppError("File is empty", status_code=422, code="EMPTY_FILE")
    if _extension(filename) not in ALLOWED_EXTENSIONS:
        raise AppError(
            f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            status_code=422,
            code="INVALID_FILE_TYPE",
        )
    extension = _extension(filename)
    if content_type not in ALLOWED_MIME_TYPES or MIME_TYPE_BY_EXTENSION.get(extension) != content_type:
        raise AppError(
            "The declared file type does not match the filename",
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


async def read_upload_limited(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Read an upload with a hard cap even if request metadata is dishonest."""
    limit = max_bytes or settings.max_upload_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    consumed = 0
    while True:
        try:
            chunk = await file.read(min(1024 * 1024, limit + 1 - consumed))
        except TypeError:
            # A few internal test doubles implement the older no-argument
            # protocol. Real Starlette UploadFile objects always use the
            # bounded branch above.
            chunk = await file.read()
            if len(chunk) > limit:
                raise AppError(
                    "File exceeds the configured maximum size",
                    status_code=413,
                    code="FILE_TOO_LARGE",
                )
            return chunk
        if not chunk:
            break
        consumed += len(chunk)
        if consumed > limit:
            raise AppError(
                "File exceeds the configured maximum size",
                status_code=413,
                code="FILE_TOO_LARGE",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def validate_file_content(filename: str, data: bytes) -> None:
    """Reject spoofed formats and resource-exhaustion DOCX archives."""
    extension = _extension(filename)
    if extension == "pdf":
        if not data.startswith(b"%PDF"):
            raise AppError(
                "The uploaded file is not a valid PDF",
                status_code=422,
                code="INVALID_FILE_CONTENT",
            )
        return
    if extension == "txt":
        if b"\x00" in data:
            raise AppError(
                "The uploaded text file contains binary data",
                status_code=422,
                code="INVALID_FILE_CONTENT",
            )
        try:
            data.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise AppError(
                "Text uploads must use UTF-8 encoding",
                status_code=422,
                code="INVALID_FILE_CONTENT",
            ) from exc
        return
    if extension != "docx":
        return

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > settings.max_docx_archive_entries:
                raise AppError(
                    "The DOCX archive contains too many entries",
                    status_code=422,
                    code="UNSAFE_ARCHIVE",
                )
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise AppError(
                    "The uploaded file is not a valid DOCX document",
                    status_code=422,
                    code="INVALID_FILE_CONTENT",
                )
            uncompressed = 0
            for entry in entries:
                normalized = entry.filename.replace("\\", "/")
                if normalized.startswith("/") or ".." in normalized.split("/"):
                    raise AppError(
                        "The DOCX archive contains an unsafe path",
                        status_code=422,
                        code="UNSAFE_ARCHIVE",
                    )
                uncompressed += entry.file_size
                if uncompressed > settings.max_docx_uncompressed_bytes:
                    raise AppError(
                        "The DOCX archive expands beyond the safe limit",
                        status_code=422,
                        code="UNSAFE_ARCHIVE",
                    )
                if (
                    entry.file_size > 0
                    and entry.compress_size == 0
                    or entry.compress_size > 0
                    and entry.file_size / entry.compress_size
                    > settings.max_docx_compression_ratio
                ):
                    raise AppError(
                        "The DOCX archive compression ratio is unsafe",
                        status_code=422,
                        code="UNSAFE_ARCHIVE",
                    )
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise AppError(
            "The uploaded file is not a valid DOCX document",
            status_code=422,
            code="INVALID_FILE_CONTENT",
        ) from exc


async def ingest_document(
    file: UploadFile,
    knowledge_source_id: str,
    user_id: str,
) -> IngestResponse:
    data = await read_upload_limited(file)

    _validate(file.filename or "", file.content_type or "", len(data))
    validate_file_content(file.filename or "", data)

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
    safe_name = _safe_filename(file.filename or "")
    object_key = f"{ks['institution_id']}/{knowledge_source_id}/{version_uuid}/{safe_name}"

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
    except AppError:
        delete_file(r2, settings.r2_bucket, object_key)
        raise
    except Exception as exc:
        delete_file(r2, settings.r2_bucket, object_key)
        # Phase 6.21 — production hardening: the raw exception may carry SQL
        # text, storage paths, or provider detail; keep it server-side only.
        logger.exception(
            "Document version registration failed (document_id=%s)", doc_id
        )
        raise AppError(
            "Document processing failed during registration",
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
