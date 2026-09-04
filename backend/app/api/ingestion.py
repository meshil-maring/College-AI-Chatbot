from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.security import get_current_user
from app.schemas.ingestion import IngestResponse
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(
    file: UploadFile,
    knowledge_source_id: str = Form(...),
    current_user: dict = Depends(get_current_user),
) -> IngestResponse:
    return await ingest_document(
        file=file,
        knowledge_source_id=knowledge_source_id,
        user_id=current_user["user_id"],
    )
