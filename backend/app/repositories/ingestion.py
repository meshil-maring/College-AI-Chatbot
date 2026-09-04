from supabase import Client


def get_knowledge_source(client: Client, knowledge_source_id: str) -> dict | None:
    response = (
        client.table("knowledge_sources")
        .select("knowledge_source_id, institution_id, title, source_type, lifecycle_status")
        .eq("knowledge_source_id", knowledge_source_id)
        .maybe_single()
        .execute()
    )
    return response.data


def create_document(client: Client, knowledge_source_id: str) -> dict:
    response = (
        client.table("documents")
        .insert({"knowledge_source_id": knowledge_source_id})
        .execute()
    )
    return response.data[0]


def create_document_version(
    client: Client,
    document_id: str,
    user_id: str,
    original_filename: str,
    file_type: str,
    mime_type: str,
    file_size_bytes: int,
    storage_bucket: str,
    storage_object_key: str,
    file_checksum: str,
) -> dict:
    response = (
        client.table("document_versions")
        .insert({
            "document_id": document_id,
            "version_number": 1,
            "original_filename": original_filename,
            "file_type": file_type,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "storage_provider": "r2",
            "storage_bucket": storage_bucket,
            "storage_object_key": storage_object_key,
            "file_checksum": file_checksum,
            "lifecycle_status": "draft",
            "created_by_user_id": user_id,
        })
        .execute()
    )
    return response.data[0]


def create_processing_run(
    client: Client,
    document_version_id: str,
    processor_name: str,
    processor_version: str,
) -> dict:
    response = (
        client.table("document_processing_runs")
        .insert({
            "document_version_id": document_version_id,
            "status": "queued",
            "processor_name": processor_name,
            "processor_version": processor_version,
        })
        .execute()
    )
    return response.data[0]


def get_processing_run_with_version(client: Client, processing_run_id: str) -> dict | None:
    response = (
        client.table("document_processing_runs")
        .select(
            "processing_run_id, status, embedding_status, document_version_id, "
            "document_versions(document_version_id, storage_bucket, storage_object_key, file_type)"
        )
        .eq("processing_run_id", processing_run_id)
        .maybe_single()
        .execute()
    )
    return response.data


def update_run_status(
    client: Client,
    processing_run_id: str,
    status: str,
    started_at: str | None = None,
    completed_at: str | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict = {"status": status}
    if started_at is not None:
        payload["started_at"] = started_at
    if completed_at is not None:
        payload["completed_at"] = completed_at
    if error_message is not None:
        payload["error_message"] = error_message
    client.table("document_processing_runs").update(payload).eq(
        "processing_run_id", processing_run_id
    ).execute()


def store_extracted_text(
    client: Client,
    document_version_id: str,
    extracted_text: str,
) -> None:
    client.table("document_versions").update(
        {"extracted_text": extracted_text}
    ).eq("document_version_id", document_version_id).execute()


def get_extracted_text(client: Client, document_version_id: str) -> str | None:
    response = (
        client.table("document_versions")
        .select("extracted_text")
        .eq("document_version_id", document_version_id)
        .maybe_single()
        .execute()
    )
    if response.data is None:
        return None
    return response.data.get("extracted_text")


def delete_chunks_for_run(client: Client, processing_run_id: str) -> None:
    client.table("knowledge_chunks").delete().eq(
        "processing_run_id", processing_run_id
    ).execute()


def insert_chunks(client: Client, processing_run_id: str, chunks: list[dict]) -> int:
    """Insert chunk dicts into knowledge_chunks. Returns the count inserted."""
    if not chunks:
        return 0
    rows = [
        {
            "processing_run_id": processing_run_id,
            "chunk_sequence": c["chunk_sequence"],
            "content_text": c["content_text"],
            "token_count": c["token_count"],
            "section_title": c.get("section_title"),
            "page_start": None,
            "page_end": None,
            "source_locator": None,
        }
        for c in chunks
    ]
    client.table("knowledge_chunks").insert(rows).execute()
    return len(rows)
