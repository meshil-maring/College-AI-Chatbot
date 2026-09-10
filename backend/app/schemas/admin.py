"""Admin module contracts (Phase Admin-2 — Backend Contracts & Repositories).

These schemas are the backend contracts shared by the admin repositories and
the (future) Admin API. Column names mirror the Admin-1 database schema:

  * knowledge_sources / documents / document_versions  (existing tables)
  * faqs, notices, admin_audit_log                     (Phase Admin-1 tables)
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Knowledge sources
# ============================================================================


class KnowledgeSourceCreate(BaseModel):
    """Payload for creating a knowledge source."""

    institution_id: UUID
    source_type: str
    title: str
    description: str | None = None
    authority_level: str = "standard"
    lifecycle_status: str = "draft"
    effective_from: date | None = None
    effective_until: date | None = None


class KnowledgeSourceUpdate(BaseModel):
    """Partial update payload for a knowledge source."""

    title: str | None = None
    description: str | None = None
    authority_level: str | None = None
    lifecycle_status: str | None = None
    effective_from: date | None = None
    effective_until: date | None = None


class KnowledgeSourceResponse(BaseModel):
    """A knowledge source row as returned to the admin layer."""

    knowledge_source_id: UUID
    institution_id: UUID
    source_type: str
    title: str
    description: str | None
    authority_level: str
    lifecycle_status: str
    effective_from: date | None
    effective_until: date | None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Documents and document versions
# ============================================================================


class DocumentVersionCreate(BaseModel):
    """Payload for registering a new version of an existing document."""

    document_id: UUID
    original_filename: str
    file_type: str
    mime_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    storage_bucket: str
    storage_object_key: str
    file_checksum: str | None = None
    version_label: str | None = None


class DocumentVersionResponse(BaseModel):
    """A single document version row."""

    document_version_id: UUID
    document_id: UUID
    version_number: int
    version_label: str | None
    original_filename: str
    file_type: str
    mime_type: str | None
    file_size_bytes: int | None
    storage_bucket: str
    storage_object_key: str
    file_checksum: str | None
    lifecycle_status: str
    supersedes_version_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentWithVersionsResponse(BaseModel):
    """A document with its full version history (newest-first in the UI)."""

    document_id: UUID
    knowledge_source_id: UUID
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse] = Field(default_factory=list)


# ============================================================================
# FAQs
# ============================================================================


class FaqCreate(BaseModel):
    """Payload for creating a FAQ (global when institution_id is omitted)."""

    institution_id: UUID | None = None
    category: str = "general"
    question: str
    answer: str
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class FaqUpdate(BaseModel):
    """Partial update payload for a FAQ."""

    category: str | None = None
    question: str | None = None
    answer: str | None = None
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_published: bool | None = None


class FaqResponse(BaseModel):
    """A FAQ row as returned to the admin layer."""

    faq_id: UUID
    institution_id: UUID | None
    category: str
    question: str
    answer: str
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Notices
# ============================================================================


class NoticeCreate(BaseModel):
    """Payload for creating a notice (global when institution_id is omitted)."""

    institution_id: UUID | None = None
    title: str
    content: str
    category: str = "general"
    priority: str = "normal"
    is_active: bool = True
    is_pinned: bool = False
    published_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeUpdate(BaseModel):
    """Partial update payload for a notice."""

    title: str | None = None
    content: str | None = None
    category: str | None = None
    priority: str | None = None
    is_active: bool | None = None
    is_pinned: bool | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeResponse(BaseModel):
    """A notice row as returned to the admin layer."""

    notice_id: UUID
    institution_id: UUID | None
    title: str
    content: str
    category: str
    priority: str
    is_active: bool
    is_pinned: bool
    published_at: datetime | None
    expires_at: datetime | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Admin audit log
# ============================================================================


class AdminAuditLogCreate(BaseModel):
    """Payload for recording one privileged admin action."""

    actor_user_id: UUID
    action: str
    table_name: str | None = None
    record_id: str | None = None
    record_data: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: str = "success"


class AdminAuditLogResponse(BaseModel):
    """An audit-log row as returned to the admin layer."""

    audit_id: UUID
    actor_user_id: UUID
    action: str
    table_name: str | None
    record_id: str | None
    record_data: dict | None
    ip_address: str | None
    user_agent: str | None
    status: str
    performed_at: datetime