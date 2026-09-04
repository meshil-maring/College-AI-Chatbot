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
