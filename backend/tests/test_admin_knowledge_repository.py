"""Phase Admin-2 tests for the admin knowledge repository."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.repositories import admin_knowledge as repo
from app.schemas.admin import (
    DocumentVersionCreate,
    FaqCreate,
    FaqUpdate,
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
    NoticeCreate,
    NoticeUpdate,
)

INSTITUTION_ID = uuid4()
KS_ID = uuid4()
DOC_ID = uuid4()
LATEST_VERSION_ID = uuid4()


def _ks_create_payload() -> KnowledgeSourceCreate:
    return KnowledgeSourceCreate(
        institution_id=INSTITUTION_ID,
        source_type="handbook",
        title="Student Handbook",
    )


# ============================================================================
# Knowledge sources
# ============================================================================


def test_create_knowledge_source_inserts_serialized_row() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"knowledge_source_id": str(KS_ID)}
    ]

    row = repo.create_knowledge_source(client, _ks_create_payload(), uuid4())

    assert row == {"knowledge_source_id": str(KS_ID)}
    client.table.assert_called_once_with("knowledge_sources")
    inserted = client.table.return_value.insert.call_args.args[0]
    assert inserted["institution_id"] == str(INSTITUTION_ID)
    assert inserted["title"] == "Student Handbook"
    assert inserted["lifecycle_status"] == "draft"
    assert "created_by_user_id" in inserted


def test_list_knowledge_sources_filters_by_institution() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.execute.return_value.data = [
        {"knowledge_source_id": str(KS_ID)}
    ]

    rows = repo.list_knowledge_sources(client, INSTITUTION_ID)

    assert rows == [{"knowledge_source_id": str(KS_ID)}]
    client.table.assert_called_once_with("knowledge_sources")
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "institution_id", str(INSTITUTION_ID)
    )


def test_list_knowledge_sources_can_exclude_archived() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    rows = repo.list_knowledge_sources(client, INSTITUTION_ID, include_archived=False)

    assert rows == []
    chain.in_.assert_called_once_with(
        "lifecycle_status",
        ["draft", "under_review", "approved", "published"],
    )


def test_get_knowledge_source_detail_returns_row_or_none() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "knowledge_source_id": str(KS_ID)
    }

    row = repo.get_knowledge_source_detail(client, KS_ID)

    assert row == {"knowledge_source_id": str(KS_ID)}
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "knowledge_source_id", str(KS_ID)
    )


def test_update_knowledge_source_sends_only_set_fields() -> None:
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"lifecycle_status": "published"}
    ]

    row = repo.update_knowledge_source(
        client, KS_ID, KnowledgeSourceUpdate(lifecycle_status="published")
    )

    assert row == {"lifecycle_status": "published"}
    client.table.return_value.update.assert_called_once_with(
        {"lifecycle_status": "published"}
    )
    client.table.return_value.update.return_value.eq.assert_called_once_with(
        "knowledge_source_id", str(KS_ID)
    )


def test_update_knowledge_source_rejects_empty_payload() -> None:
    client = MagicMock()

    with pytest.raises(ValueError, match="empty"):
        repo.update_knowledge_source(client, KS_ID, KnowledgeSourceUpdate())

    client.table.assert_not_called()


# ============================================================================
# Documents and document versions
# ============================================================================


def test_list_documents_for_source_filters_by_knowledge_source() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.execute.return_value.data = [
        {"document_id": str(DOC_ID)}
    ]

    rows = repo.list_documents_for_source(client, KS_ID)

    assert rows == [{"document_id": str(DOC_ID)}]
    client.table.assert_called_once_with("documents")
    client.table.return_value.select.return_value.eq.assert_called_once_with(
        "knowledge_source_id", str(KS_ID)
    )


def test_get_document_with_versions_selects_nested_versions() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.maybe_single.return_value.execute.return_value.data = {
        "document_id": str(DOC_ID),
        "document_versions": [],
    }

    row = repo.get_document_with_versions(client, DOC_ID)

    assert row["document_id"] == str(DOC_ID)
    client.table.assert_called_once_with("documents")
    select_arg = client.table.return_value.select.call_args.args[0]
    assert "document_versions(*)" in select_arg


def test_create_next_document_version_first_version_has_no_predecessor() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value.data = None
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"version_number": 1}
    ]

    payload = DocumentVersionCreate(
        document_id=DOC_ID,
        original_filename="handbook.pdf",
        file_type="pdf",
        storage_bucket="college-documents",
        storage_object_key="documents/handbook.pdf",
    )
    created_by = uuid4()

    created = repo.create_next_document_version(client, payload, created_by)

    assert created == {"version_number": 1}
    row = client.table.return_value.insert.call_args.args[0]
    assert row["version_number"] == 1
    assert row["document_id"] == str(DOC_ID)
    assert row["lifecycle_status"] == "draft"
    assert row["storage_provider"] == "r2"
    assert row["created_by_user_id"] == str(created_by)
    assert "supersedes_version_id" not in row
    # No previous version -> nothing to supersede.
    client.table.return_value.update.assert_not_called()


def test_create_next_document_version_increments_and_supersedes() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value.data = {
        "document_version_id": str(LATEST_VERSION_ID),
        "version_number": 3,
        "lifecycle_status": "published",
    }
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"version_number": 4}
    ]

    payload = DocumentVersionCreate(
        document_id=DOC_ID,
        original_filename="handbook-v2.pdf",
        file_type="pdf",
        storage_bucket="college-documents",
        storage_object_key="documents/handbook-v2.pdf",
        version_label="Revision B",
    )
    created_by = uuid4()

    created = repo.create_next_document_version(client, payload, created_by)

    assert created == {"version_number": 4}
    row = client.table.return_value.insert.call_args.args[0]
    assert row["version_number"] == 4
    assert row["supersedes_version_id"] == str(LATEST_VERSION_ID)
    assert row["version_label"] == "Revision B"
    # Previous latest version is moved to superseded.
    client.table.return_value.update.assert_called_once_with(
        {"lifecycle_status": "superseded"}
    )
    client.table.return_value.update.return_value.eq.assert_called_once_with(
        "document_version_id", str(LATEST_VERSION_ID)
    )


def test_create_next_document_version_does_not_resupersede() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value.eq.return_value
    chain.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value.data = {
        "document_version_id": str(LATEST_VERSION_ID),
        "version_number": 2,
        "lifecycle_status": "superseded",
    }
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"version_number": 3}
    ]

    payload = DocumentVersionCreate(
        document_id=DOC_ID,
        original_filename="handbook-v3.pdf",
        file_type="pdf",
        storage_bucket="college-documents",
        storage_object_key="documents/handbook-v3.pdf",
    )

    repo.create_next_document_version(client, payload, uuid4())

    client.table.return_value.update.assert_not_called()


def test_update_document_version_lifecycle_updates_status() -> None:
    client = MagicMock()
    version_id = uuid4()

    repo.update_document_version_lifecycle(client, version_id, "approved")

    client.table.assert_called_once_with("document_versions")
    client.table.return_value.update.assert_called_once_with(
        {"lifecycle_status": "approved"}
    )
    client.table.return_value.update.return_value.eq.assert_called_once_with(
        "document_version_id", str(version_id)
    )


# ============================================================================
# FAQs
# ============================================================================


def test_list_faqs_active_only_by_default() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"faq_id": "1"}
    ]

    rows = repo.list_faqs(client, INSTITUTION_ID, category="general")

    assert rows == [{"faq_id": "1"}]
    client.table.assert_called_once_with("faqs")
    chain.eq.assert_called_once_with("institution_id", str(INSTITUTION_ID))
    chain.eq.return_value.eq.assert_called_once_with("category", "general")
    chain.eq.return_value.eq.return_value.eq.assert_called_once_with("is_active", True)


def test_list_faqs_without_institution_returns_global_and_scoped() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

    rows = repo.list_faqs(client)

    assert rows == []
    chain.eq.assert_called_once_with("is_active", True)


def test_create_faq_inserts_payload() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"faq_id": "1"}
    ]

    row = repo.create_faq(
        client, FaqCreate(institution_id=INSTITUTION_ID, question="Q", answer="A")
    )

    assert row == {"faq_id": "1"}
    inserted = client.table.return_value.insert.call_args.args[0]
    assert inserted["institution_id"] == str(INSTITUTION_ID)
    assert inserted["question"] == "Q"
    assert inserted["is_active"] is True


def test_update_and_delete_faq() -> None:
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"faq_id": "1"}
    ]

    row = repo.update_faq(client, "1", FaqUpdate(answer="A2"))
    assert row == {"faq_id": "1"}
    client.table.return_value.update.assert_called_once_with({"answer": "A2"})

    repo.delete_faq(client, "1")
    client.table.return_value.delete.assert_called_once()
    client.table.return_value.delete.return_value.eq.assert_called_once_with(
        "faq_id", "1"
    )


# ============================================================================
# Notices
# ============================================================================


def test_list_notices_orders_pinned_first() -> None:
    client = MagicMock()
    chain = client.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"notice_id": "1"}
    ]

    rows = repo.list_notices(client, INSTITUTION_ID)

    assert rows == [{"notice_id": "1"}]
    chain.eq.assert_called_once_with("institution_id", str(INSTITUTION_ID))
    chain.eq.return_value.eq.assert_called_once_with("is_active", True)
    chain.eq.return_value.eq.return_value.order.assert_called_once_with(
        "is_pinned", desc=True
    )
    chain.eq.return_value.eq.return_value.order.return_value.order.assert_called_once_with(
        "published_at", desc=True
    )


def test_create_notice_sets_created_by() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"notice_id": "1"}
    ]
    created_by = uuid4()

    row = repo.create_notice(
        client, NoticeCreate(title="T", content="C"), created_by
    )

    assert row == {"notice_id": "1"}
    inserted = client.table.return_value.insert.call_args.args[0]
    assert inserted["created_by"] == str(created_by)
    assert inserted["title"] == "T"
    assert inserted["priority"] == "normal"


def test_create_notice_without_creator_leaves_created_by_absent() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {"notice_id": "1"}
    ]

    repo.create_notice(client, NoticeCreate(title="T", content="C"))

    inserted = client.table.return_value.insert.call_args.args[0]
    assert "created_by" not in inserted


def test_update_and_delete_notice() -> None:
    client = MagicMock()
    client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"notice_id": "1"}
    ]

    row = repo.update_notice(client, "1", NoticeUpdate(is_pinned=True))
    assert row == {"notice_id": "1"}
    client.table.return_value.update.assert_called_once_with({"is_pinned": True})

    repo.delete_notice(client, "1")
    client.table.return_value.delete.assert_called_once()
    client.table.return_value.delete.return_value.eq.assert_called_once_with(
        "notice_id", "1"
    )


def test_update_notice_rejects_empty_payload() -> None:
    client = MagicMock()

    with pytest.raises(ValueError, match="empty"):
        repo.update_notice(client, "1", NoticeUpdate())

    client.table.assert_not_called()