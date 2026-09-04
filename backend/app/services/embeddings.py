from collections.abc import Iterable

from openai import OpenAI

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.embeddings import (
    delete_embeddings_for_run,
    get_chunks_for_run,
    update_run_embedding_status,
    upsert_chunk_embeddings,
)
from app.repositories.ingestion import get_processing_run_with_version


def _safe_error_message(error: Exception) -> str:
    message = str(error)
    if settings.openai_api_key:
        message = message.replace(settings.openai_api_key, "[redacted]")
    return message[:1000]


def _embedding_values(response: object) -> list[list[float]]:
    data = getattr(response, "data", None)
    if data is None:
        raise ValueError("OpenAI returned no embedding data")
    values = []
    for item in data:
        embedding = getattr(item, "embedding", None)
        if embedding is None and isinstance(item, dict):
            embedding = item.get("embedding")
        if embedding is None:
            raise ValueError("OpenAI returned an embedding without a vector")
        values.append(embedding)
    return values


def _batches(items: list[dict], size: int) -> Iterable[list[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def embed_processing_run(processing_run_id: str) -> int:
    """Generate and persist embeddings for all chunks in a processing run."""
    db = get_admin_client()
    run = get_processing_run_with_version(db, processing_run_id)
    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")

    embedding_status = run.get("embedding_status")
    if embedding_status == "embedded":
        return 0
    if embedding_status not in (None, "failed"):
        raise AppError(
            f"Run is not available for embedding (current: {embedding_status})",
            status_code=409,
            code="RUN_NOT_EMBEDDABLE",
        )

    update_run_embedding_status(db, processing_run_id, "processing")
    try:
        chunks = get_chunks_for_run(db, processing_run_id)
        if not chunks:
            raise AppError(
                "Processing run has no chunks to embed",
                status_code=422,
                code="NO_CHUNKS",
            )

        delete_embeddings_for_run(db, processing_run_id, settings.embedding_model)
        client = OpenAI(api_key=settings.openai_api_key)
        total = 0

        if settings.embedding_batch_size <= 0:
            raise ValueError("Embedding batch size must be greater than zero")

        for batch in _batches(chunks, settings.embedding_batch_size):
            response = client.embeddings.create(
                input=[chunk["content_text"] for chunk in batch],
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
            )
            vectors = _embedding_values(response)
            if len(vectors) != len(batch):
                raise ValueError(
                    "OpenAI returned an embedding count that does not match the chunk count"
                )
            for vector in vectors:
                if len(vector) != settings.embedding_dimensions:
                    raise ValueError(
                        "OpenAI returned an embedding with an unexpected number of dimensions"
                    )

            total += upsert_chunk_embeddings(
                db,
                settings.embedding_model,
                settings.embedding_dimensions,
                [
                    {"chunk_id": chunk["chunk_id"], "embedding": vector}
                    for chunk, vector in zip(batch, vectors)
                ],
            )

        update_run_embedding_status(db, processing_run_id, "embedded")
        return total
    except AppError as exc:
        error_message = _safe_error_message(exc)
        update_run_embedding_status(db, processing_run_id, "failed", error_message)
        raise AppError(error_message, status_code=exc.status_code, code=exc.code) from exc
    except Exception as exc:
        error_message = _safe_error_message(exc)
        update_run_embedding_status(db, processing_run_id, "failed", error_message)
        raise AppError(error_message, status_code=500, code="EMBEDDING_FAILED") from exc