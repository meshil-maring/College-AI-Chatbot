"""One authoritative application policy for anonymous knowledge access."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from app.repositories import public_knowledge as repository
from app.schemas.generation import RetrievedChunk

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
    today = on_date or datetime.now(UTC).date()
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
        """Return canonical, fully verified chunks in retrieval order.

        The vector result is an untrusted candidate.  In particular, its text
        and provenance identifiers are not allowed to reach the model merely
        because its chunk UUID exists.  Eligible results are reconstructed
        from the repository row after the complete provenance chain passes.
        Duplicate chunk IDs are collapsed without changing similarity order.
        """
        chunk_ids = {
            str(chunk.chunk_id)
            for chunk in chunks
            if getattr(chunk, "chunk_id", None)
        }
        rows = repository.get_chunk_provenance(self.client, chunk_ids)
        canonical_by_id: dict[str, dict] = {}
        for row in rows:
            run = _one(row.get("document_processing_runs")) or row
            normalized = normalize_provenance(run)
            version = normalized.get("document_version") or {}
            document = normalized.get("document") or {}
            source = normalized.get("knowledge_source") or {}
            source_id = str(
                source.get("knowledge_source_id", "")
            )
            content_text = row.get("content_text")
            if (
                row.get("chunk_id")
                and row.get("processing_run_id")
                and str(row.get("processing_run_id"))
                == str(normalized.get("processing_run_id"))
                and isinstance(content_text, str)
                and bool(content_text.strip())
                and is_public_provenance(normalized, self.institution_id)
                and (
                    allowed_source_ids is None
                    or source_id in allowed_source_ids
                )
            ):
                canonical_by_id[str(row["chunk_id"])] = {
                    "content_text": content_text,
                    "processing_run_id": str(row["processing_run_id"]),
                    "document_id": document.get("document_id"),
                    "document_version_id": version.get("document_version_id"),
                    "chunk_sequence": row.get("chunk_sequence"),
                    "section_title": row.get("section_title"),
                    "source_title": source.get("title"),
                    "source_type": source.get("source_type"),
                }

        verified: list[RetrievedChunk] = []
        seen_chunk_ids: set[str] = set()
        for candidate in chunks:
            candidate_id = str(getattr(candidate, "chunk_id", ""))
            canonical = canonical_by_id.get(candidate_id)
            if not canonical or candidate_id in seen_chunk_ids:
                continue

            metadata = getattr(candidate, "metadata", None) or {}
            candidate_run_id = metadata.get("processing_run_id")
            if (
                candidate_run_id is not None
                and str(candidate_run_id) != canonical["processing_run_id"]
            ):
                continue
            for field in ("document_id", "document_version_id"):
                supplied = getattr(candidate, field, None)
                authoritative = canonical[field]
                if supplied is not None and str(supplied) != str(authoritative):
                    break
            else:
                safe_metadata = {
                    key: canonical[key]
                    for key in (
                        "processing_run_id",
                        "chunk_sequence",
                        "section_title",
                        "source_title",
                        "source_type",
                    )
                    if canonical[key] is not None
                }
                verified.append(
                    RetrievedChunk(
                        chunk_id=candidate.chunk_id,
                        document_id=canonical["document_id"],
                        document_version_id=canonical["document_version_id"],
                        text=canonical["content_text"],
                        similarity_score=candidate.similarity_score,
                        metadata=safe_metadata,
                    )
                )
                seen_chunk_ids.add(candidate_id)
        return verified
