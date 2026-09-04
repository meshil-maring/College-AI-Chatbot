from pydantic import BaseModel


class IngestResponse(BaseModel):
    knowledge_source_id: str
    document_id: str
    document_version_id: str
    processing_run_id: str
    storage_object_key: str
    status: str = "queued"
