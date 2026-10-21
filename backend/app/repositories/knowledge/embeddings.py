from supabase import Client


def get_chunks_for_run(client: Client, processing_run_id: str) -> list[dict]:
    response = (
        client.table("knowledge_chunks")
        .select("chunk_id, content_text, chunk_sequence")
        .eq("processing_run_id", processing_run_id)
        .order("chunk_sequence")
        .execute()
    )
    return response.data or []


def delete_embeddings_for_run(
    client: Client,
    processing_run_id: str,
    model_name: str,
) -> None:
    chunks = get_chunks_for_run(client, processing_run_id)
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    if not chunk_ids:
        return

    (
        client.table("chunk_embeddings")
        .delete()
        .in_("chunk_id", chunk_ids)
        .eq("model_name", model_name)
        .execute()
    )


def upsert_chunk_embeddings(
    client: Client,
    model_name: str,
    embedding_dimensions: int,
    embeddings: list[dict],
) -> int:
    if not embeddings:
        return 0

    rows = [
        {
            "chunk_id": embedding["chunk_id"],
            "model_name": model_name,
            "embedding_dimensions": embedding_dimensions,
            "embedding": embedding["embedding"],
        }
        for embedding in embeddings
    ]
    client.table("chunk_embeddings").upsert(
        rows,
        on_conflict="chunk_id,model_name",
    ).execute()
    return len(rows)


def update_run_embedding_status(
    client: Client,
    processing_run_id: str,
    embedding_status: str,
    embedding_error: str | None = None,
) -> None:
    payload: dict = {"embedding_status": embedding_status}
    if embedding_error is not None:
        payload["embedding_error"] = embedding_error[:1000]

    client.table("document_processing_runs").update(payload).eq(
        "processing_run_id", processing_run_id
    ).execute()