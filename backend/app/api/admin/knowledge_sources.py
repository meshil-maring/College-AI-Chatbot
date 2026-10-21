"""Admin knowledge sources endpoints."""

from uuid import UUID

from fastapi import Depends

from app.core.errors import AppError
from app.repositories.admin import admin_knowledge as knowledge_repo
from app.schemas.admin.admin import KnowledgeSourceCreate, KnowledgeSourceUpdate
from app.api.admin import common
from app.api.admin.dependencies import create_feature_router, _ADMIN


router = create_feature_router()


@router.post("/knowledge-sources", status_code=201)
def create_knowledge_source(
    payload: KnowledgeSourceCreate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    common.assert_row_tenant(current_user, payload.institution_id)
    db = common.get_admin_client()
    created = knowledge_repo.create_knowledge_source(db, payload, current_user["user_id"])
    common.record_audit(
        current_user,
        "knowledge_source.create",
        "knowledge_sources",
        created["knowledge_source_id"],
        {"source_type": payload.source_type, "title": payload.title},
    )
    return created


@router.get("/knowledge-sources")
def list_knowledge_sources(
    institution_id: UUID,
    include_archived: bool = True,
    limit: int = 100,
    current_user: dict = Depends(_ADMIN),
) -> list[dict]:
    institution_id = common.scope_institution(current_user, institution_id)
    db = common.get_admin_client()
    return knowledge_repo.list_knowledge_sources(
        db, institution_id, include_archived=include_archived, limit=limit
    )


@router.get("/knowledge-sources/{knowledge_source_id}")
def get_knowledge_source(
    knowledge_source_id: UUID,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = common.get_admin_client()
    row = knowledge_repo.get_knowledge_source_detail(db, knowledge_source_id)
    if row is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, row.get("institution_id"))
    return row


@router.patch("/knowledge-sources/{knowledge_source_id}")
def update_knowledge_source(
    knowledge_source_id: UUID,
    payload: KnowledgeSourceUpdate,
    current_user: dict = Depends(_ADMIN),
) -> dict:
    db = common.get_admin_client()
    existing = knowledge_repo.get_knowledge_source_detail(db, knowledge_source_id)
    if existing is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.assert_row_tenant(current_user, existing.get("institution_id"))
    updated = knowledge_repo.update_knowledge_source(db, knowledge_source_id, payload)
    if updated is None:
        raise AppError(
            "Knowledge source not found",
            status_code=404,
            code="KNOWLEDGE_SOURCE_NOT_FOUND",
        )
    common.record_audit(
        current_user,
        "knowledge_source.update",
        "knowledge_sources",
        str(knowledge_source_id),
        payload.model_dump(mode="json", exclude_unset=True),
    )
    return updated
