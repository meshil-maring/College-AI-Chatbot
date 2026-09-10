"""Phase Admin-2 tests for the admin schemas (backend contracts)."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.admin import (
    AdminAuditLogCreate,
    AdminAuditLogResponse,
    DocumentVersionCreate,
    DocumentVersionResponse,
    DocumentWithVersionsResponse,
    FaqCreate,
    FaqResponse,
    FaqUpdate,
    KnowledgeSourceCreate,
    KnowledgeSourceResponse,
    KnowledgeSourceUpdate,
    NoticeCreate,
    NoticeResponse,
    NoticeUpdate,
)

NOW = datetime(2026, 9, 9, 12, 0, 0)


# ============================================================================
# Knowledge sources
# ============================================================================


def test_knowledge_source_create_defaults() -> None:
    payload = KnowledgeSourceCreate(
        institution_id=uuid4(),
        source_type="handbook",
        title="Student Handbook",
    )

    assert payload.authority_level == "standard"
    assert payload.lifecycle_status == "draft"
    assert payload.description is None
    assert payload.effective_from is None
    assert payload.effective_until is None


def test_knowledge_source_create_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        KnowledgeSourceCreate(source_type="handbook", title="Student Handbook")
    with pytest.raises(ValidationError):
        KnowledgeSourceCreate(institution_id=uuid4(), title="Student Handbook")
    with pytest.raises(ValidationError):
        KnowledgeSourceCreate(institution_id=uuid4(), source_type="handbook")


def test_knowledge_source_update_all_optional() -> None:
    payload = KnowledgeSourceUpdate()
    assert payload.model_dump(exclude_unset=True) == {}

    payload = KnowledgeSourceUpdate(lifecycle_status="published")
    assert payload.model_dump(exclude_unset=True) == {"lifecycle_status": "published"}


def test_knowledge_source_response_round_trip() -> None:
    institution_id = uuid4()
    response = KnowledgeSourceResponse(
        knowledge_source_id=uuid4(),
        institution_id=institution_id,
        source_type="handbook",
        title="Student Handbook",
        description=None,
        authority_level="standard",
        lifecycle_status="published",
        effective_from=date(2026, 7, 1),
        effective_until=None,
        created_at=NOW,
        updated_at=NOW,
    )

    assert response.institution_id == institution_id
    data = response.model_dump(mode="json")
    assert data["effective_from"] == "2026-07-01"


# ============================================================================
# Document versions
# ============================================================================


def test_document_version_create_defaults() -> None:
    payload = DocumentVersionCreate(
        document_id=uuid4(),
        original_filename="handbook.pdf",
        file_type="pdf",
        storage_bucket="college-documents",
        storage_object_key="documents/handbook.pdf",
    )

    assert payload.mime_type is None
    assert payload.file_size_bytes is None
    assert payload.file_checksum is None
    assert payload.version_label is None


def test_document_version_response_round_trip() -> None:
    supersedes_id = uuid4()
    response = DocumentVersionResponse(
        document_version_id=uuid4(),
        document_id=uuid4(),
        version_number=2,
        version_label="Revision A",
        original_filename="handbook.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_bucket="college-documents",
        storage_object_key="documents/handbook.pdf",
        file_checksum="abc123",
        lifecycle_status="draft",
        supersedes_version_id=supersedes_id,
        created_by_user_id=uuid4(),
        created_at=NOW,
        updated_at=NOW,
    )

    data = response.model_dump(mode="json")
    assert data["version_number"] == 2
    assert data["supersedes_version_id"] == str(supersedes_id)


def test_document_with_versions_defaults_to_empty_history() -> None:
    response = DocumentWithVersionsResponse(
        document_id=uuid4(),
        knowledge_source_id=uuid4(),
        created_at=NOW,
        updated_at=NOW,
    )

    assert response.versions == []


# ============================================================================
# FAQs
# ============================================================================


def test_faq_create_defaults() -> None:
    payload = FaqCreate(question="How do I register?", answer="Via the portal.")

    assert payload.institution_id is None
    assert payload.category == "general"
    assert payload.display_order == 0
    assert payload.is_active is True


def test_faq_create_rejects_negative_display_order() -> None:
    with pytest.raises(ValidationError):
        FaqCreate(question="Q", answer="A", display_order=-1)


def test_faq_update_all_optional() -> None:
    assert FaqUpdate().model_dump(exclude_unset=True) == {}
    payload = FaqUpdate(is_active=False)
    assert payload.model_dump(exclude_unset=True) == {"is_active": False}


def test_faq_response_accepts_null_institution() -> None:
    response = FaqResponse(
        faq_id=uuid4(),
        institution_id=None,
        category="general",
        question="Q",
        answer="A",
        display_order=1,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    assert response.institution_id is None


# ============================================================================
# Notices
# ============================================================================


def test_notice_create_defaults() -> None:
    payload = NoticeCreate(title="Exam schedule", content="Midterms next week.")

    assert payload.institution_id is None
    assert payload.category == "general"
    assert payload.priority == "normal"
    assert payload.is_active is True
    assert payload.is_pinned is False
    assert payload.published_at is None
    assert payload.expires_at is None


def test_notice_update_all_optional() -> None:
    assert NoticeUpdate().model_dump(exclude_unset=True) == {}
    payload = NoticeUpdate(is_pinned=True, priority="high")
    assert payload.model_dump(exclude_unset=True) == {
        "is_pinned": True,
        "priority": "high",
    }


def test_notice_response_round_trip() -> None:
    response = NoticeResponse(
        notice_id=uuid4(),
        institution_id=uuid4(),
        title="Exam schedule",
        content="Midterms next week.",
        category="exam",
        priority="high",
        is_active=True,
        is_pinned=True,
        published_at=NOW,
        expires_at=None,
        created_by=None,
        created_at=NOW,
        updated_at=NOW,
    )

    data = response.model_dump(mode="json")
    assert data["published_at"].startswith("2026-09-09")


# ============================================================================
# Admin audit log
# ============================================================================


def test_audit_log_create_defaults() -> None:
    payload = AdminAuditLogCreate(actor_user_id=uuid4(), action="faq.create")

    assert payload.table_name is None
    assert payload.record_id is None
    assert payload.record_data is None
    assert payload.ip_address is None
    assert payload.user_agent is None
    assert payload.status == "success"


def test_audit_log_create_requires_actor_and_action() -> None:
    with pytest.raises(ValidationError):
        AdminAuditLogCreate(action="faq.create")
    with pytest.raises(ValidationError):
        AdminAuditLogCreate(actor_user_id=uuid4())


def test_audit_log_response_round_trip() -> None:
    record_data = {"question": "Q"}
    response = AdminAuditLogResponse(
        audit_id=uuid4(),
        actor_user_id=uuid4(),
        action="faq.create",
        table_name="faqs",
        record_id="123",
        record_data=record_data,
        ip_address="127.0.0.1",
        user_agent="pytest",
        status="success",
        performed_at=NOW,
    )

    data = response.model_dump(mode="json")
    assert data["record_data"] == record_data
    assert data["performed_at"].startswith("2026-09-09")