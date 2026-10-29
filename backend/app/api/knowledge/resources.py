"""Shared authenticated library and draft/review endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import require_institution_roles
from app.schemas.knowledge.resources import (
    CreateResource, DraftFields, ResourceItem, ResourceList, ReviewAction,
    ReviewCommand, RevisionItem, RevisionList, UpdateDraft,
)
from app.services.knowledge.resources import operations
from app.services.knowledge.resources.uploads import read_revision
from app.services.ai.chat_support.resource_scope import read_context
from app.schemas.ai.resource_context import ResourceChatContext

router = APIRouter(prefix='/knowledge', tags=['learning-resources'])
_READ = require_institution_roles('admin', 'faculty', 'staff', 'student')
_WRITE = require_institution_roles('admin', 'faculty', 'staff')


@router.get('/resources', response_model=ResourceList)
def list_resources(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
                   user: dict = Depends(_READ)):
    return operations.resources(user, limit=limit, offset=offset)


@router.get('/resources/{source_id}', response_model=ResourceItem)
def get_resource(source_id: UUID, user: dict = Depends(_READ)):
    return operations.resources(user, source_id=source_id)['items'][0]


@router.get('/resources/{source_id}/chat-context', response_model=ResourceChatContext)
def get_chat_context(source_id: UUID, user: dict = Depends(_READ)):
    return read_context(None, user['user_id'], user['institution_id'], source_id)


@router.post('/resources', response_model=RevisionItem, status_code=201)
def create_resource(payload: CreateResource, user: dict = Depends(_WRITE)):
    return operations.save_draft(user, payload)


@router.post('/resources/{source_id}/revisions', response_model=RevisionItem, status_code=201)
def create_revision(source_id: UUID, payload: DraftFields, user: dict = Depends(_WRITE)):
    return operations.save_draft(user, payload, source_id=source_id)


@router.patch('/resources/{source_id}/revisions/{revision_id}', response_model=RevisionItem)
def update_revision(source_id: UUID, revision_id: UUID, payload: UpdateDraft, user: dict = Depends(_WRITE)):
    return operations.save_draft(user, payload, source_id=source_id,
        revision_id=revision_id, expected_version=payload.expected_version)


@router.get('/revisions', response_model=RevisionList)
def list_revisions(view: Literal['own', 'review'] = 'own', limit: int = Query(20, ge=1, le=100),
                   offset: int = Query(0, ge=0, le=100000), user: dict = Depends(_WRITE)):
    return operations.revisions(user, review=view == 'review', limit=limit, offset=offset)


@router.get('/revisions/{revision_id}', response_model=RevisionItem)
def get_revision(revision_id: UUID, user: dict = Depends(_WRITE)):
    return read_revision(user, revision_id)


@router.post('/revisions/{revision_id}/{action}', response_model=RevisionItem)
def review_revision(revision_id: UUID, action: ReviewAction, command: ReviewCommand, user: dict = Depends(_WRITE)):
    return operations.decide(user, revision_id, action, command)
