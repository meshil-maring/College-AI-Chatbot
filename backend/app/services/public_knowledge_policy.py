"""One authoritative application policy for anonymous knowledge access."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.repositories import public_knowledge as repository


PUBLIC_VISIBILITY = "public"
PUBLISHED_LIFECYCLE = "published"
READY_PROCESSING_STATUS = "ready"
EMBEDDED_STATUS = "embedded"


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def is_effective(row: dict, *, on_date: date | None = None) -> bool:
    """Return false for malformed or out-of-window lifecycle dates."""
    today = on_date or date.today()
    raw_from = row.get("effective_from")
    raw_until = row.get("effective_until")
    effective_from = _as_date(raw_from)
    effective_until = _as_date(raw_until)
    if raw_from not in (None, "") and effective_from is None:
        return False
    if raw_until not in (None, "") and effective_until is None:
        return False
    return not (
        (effective_from is not None and effective_from > today)
        or (effective_until is not None and effective_until < today)
    )


def is_public_source(
    source: dict | None,
    institution_id: UUID | str,
    *,
    on_date: date | None = None,
) -> bool:
    """Authorize a source without inferring visibility from source_type."""
    if not isinstance(source, dict):
        return False
    return (
        str(source.get("institution_id")) == str(institution_id)
        and source.get("visibility") == PUBLIC_VISIBILITY
        and source.get("lifecycle_status") == PUBLISHED_LIFECYCLE
        and is_effective(source, on_date=on_date)
    )


def _one(value: Any) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), None)
    return None


def normalize_provenance(run: dict) -> dict:
    """Flatten the PostgREST provenance chain into policy-testable fields."""
    version = _one(run.get("document_versions")) or {}
    document = _one(version.get("documents")) or {}
    source = _one(document.get("knowledge_sources")) or {}
    # The fallback fields support simple repository fakes without weakening
    # production: absent visibility/lifecycle values still fail closed.
    return {
        "processing_run_id": run.get("processing_run_id"),
        "processing_status": run.get("status"),
        "embedding_status": run.get("embedding_status"),
        "completed_at": run.get("completed_at"),
        "document_version": version,
        "document": document,
        "knowledge_source": source,
    }


def is_public_provenance(
    provenance: dict,
    institution_id: UUID | str,
    *,
    on_date: date | None = None,
) -> bool:
    """Evaluate source, version, and processing validity as one predicate."""
    normalized = (
        normalize_provenance(provenance)
        if "processing_status" not in provenance
        else provenance
    )
    version = normalized.get("document_version") or {}
    return (
        is_public_source(
            normalized.get("knowledge_source"), institution_id, on_date=on_date
        )
        and version.get("lifecycle_status") == PUBLISHED_LIFECYCLE
        and is_effective(version, on_date=on_date)
        and normalized.get("processing_status") == READY_PROCESSING_STATUS
        and normalized.get("embedding_status") == EMBEDDED_STATUS
        and bool(normalized.get("completed_at"))
    )


class PublicKnowledgePolicy:
    """Reusable repository-backed public authorization boundary."""

    def __init__(self, client: Any, institution_id: UUID | str):
        self.client = client
        self.institution_id = institution_id

    def source_is_allowed(self, knowledge_source_id: UUID | str) -> bool:
        return is_public_source(
            repository.get_source(self.client, knowledge_source_id),
            self.institution_id,
        )

    def allowed_source_ids(self) -> set[str]:
        return {
            str(row["knowledge_source_id"])
            for row in repository.list_public_source_candidates(
                self.client, self.institution_id
            )
            if row.get("knowledge_source_id")
            and is_public_source(row, self.institution_id)
        }

    def authorize_chunks(
        self, chunks: list[Any], *, allowed_source_ids: set[str] | None = None
    ) -> list[Any]:
        chunk_ids = {
            str(chunk.chunk_id)
            for chunk in chunks
            if getattr(chunk, "chunk_id", None)
        }
        rows = repository.get_chunk_provenance(self.client, chunk_ids)
        allowed_chunks: set[str] = set()
        for row in rows:
            run = _one(row.get("document_processing_runs")) or row
            normalized = normalize_provenance(run)
            source_id = str(
                (normalized.get("knowledge_source") or {}).get(
                    "knowledge_source_id", ""
                )
            )
            if (
                row.get("chunk_id")
                and row.get("processing_run_id")
                and str(row.get("processing_run_id"))
                == str(normalized.get("processing_run_id"))
                and is_public_provenance(normalized, self.institution_id)
                and (
                    allowed_source_ids is None
                    or source_id in allowed_source_ids
                )
            ):
                allowed_chunks.add(str(row["chunk_id"]))
        return [
            chunk
            for chunk in chunks
            if getattr(chunk, "chunk_id", None)
            and str(chunk.chunk_id) in allowed_chunks
        ]
