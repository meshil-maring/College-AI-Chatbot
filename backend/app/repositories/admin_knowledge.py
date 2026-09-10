"""Admin repositories for knowledge-source, document, FAQ, and notice data.

Phase Admin-2 — Backend Contracts & Repositories.

All functions take an already-created Supabase ``Client`` as their first
argument (service-role client in production), following the existing
repository convention in ``app.repositories``.

The document-version helper ``create_next_document_version`` is additive: the
existing ``create_document_version`` helper in ``app.repositories.ingestion``
is intentionally left untouched.
"""

from uuid import UUID

from supabase import Client

from app.schemas.admin import (
    DocumentVersionCreate,
    FaqCreate,
    FaqUpdate,
    KnowledgeSourceCreate,
    KnowledgeSourceUpdate,
    NoticeCreate,
    NoticeUpdate,
)

STORAGE_PROVIDER = "r2"

KNOWLEDGE_SOURCE_COLUMNS = (
    "knowledge_source_id, institution_id, source_type, title, description, "
    "authority_level, lifecycle_status, effective_from, effective_until, "
    "created_at, updated_at"
)

DOCUMENT_COLUMNS = "document_id, knowledge_source_id, created_at, updated_at"

DOCUMENT_VERSION_COLUMNS = (
    "document_version_id, document_id, version_number, version_label, "
    "original_filename, file_type, mime_type, file_size_bytes, "
    "storage_bucket, storage_object_key, file_checksum, lifecycle_status, "
    "supersedes_version_id, created_by_user_id, created_at, updated_at"
)

FAQ_COLUMNS = (
    "faq_id, institution_id, category, question, answer, display_order, "
    "is_active, created_at, updated_at"
)

NOTICE_COLUMNS = (
    "notice_id, institution_id, title, content, category, priority, "
    "is_active, is_pinned, published_at, expires_at, created_by, "
    "created_at, updated_at"
)

# Lifecycle statuses that still count as "live" knowledge sources.
ACTIVE_LIFECYCLE_STATUSES = ["draft", "under_review", "approved", "published"]


# ============================================================================
# Knowledge sources
# ============================================================================


def create_knowledge_source(
    client: Client,
    payload: KnowledgeSourceCreate,
    created_by_user_id: UUID | str,
) -> dict:
    """Insert a new knowledge source row and return it."""
    row = payload.model_dump(mode="json")
    row["created_by_user_id"] = str(created_by_user_id)
    response = client.table("knowledge_sources").insert(row).execute()
    return response.data[0]


def list_knowledge_sources(
    client: Client,
    institution_id: UUID | str,
    include_archived: bool = True,
    limit: int = 100,
) -> list[dict]:
    """List knowledge sources for an institution, newest first."""
    query = (
        client.table("knowledge_sources")
        .select(KNOWLEDGE_SOURCE_COLUMNS)
        .eq("institution_id", str(institution_id))
    )
    if not include_archived:
        query = query.in_("lifecycle_status", ACTIVE_LIFECYCLE_STATUSES)
    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data


def get_knowledge_source_detail(
    client: Client,
    knowledge_source_id: UUID | str,
) -> dict | None:
    """Return one knowledge source row, or None when it does not exist."""
    response = (
        client.table("knowledge_sources")
        .select(KNOWLEDGE_SOURCE_COLUMNS)
        .eq("knowledge_source_id", str(knowledge_source_id))
        .maybe_single()
        .execute()
    )
    return response.data


def update_knowledge_source(
    client: Client,
    knowledge_source_id: UUID | str,
    payload: KnowledgeSourceUpdate,
) -> dict | None:
    """Apply a partial update to a knowledge source and return the updated row."""
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise ValueError("knowledge source update payload is empty")
    response = (
        client.table("knowledge_sources")
        .update(fields)
        .eq("knowledge_source_id", str(knowledge_source_id))
        .execute()
    )
    return response.data[0] if response.data else None


# ============================================================================
# Documents and document versions
# ============================================================================


def list_documents_for_source(
    client: Client,
    knowledge_source_id: UUID | str,
) -> list[dict]:
    """List documents that belong to a knowledge source, newest first."""
    response = (
        client.table("documents")
        .select(DOCUMENT_COLUMNS)
        .eq("knowledge_source_id", str(knowledge_source_id))
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_document_with_versions(client: Client, document_id: UUID | str) -> dict | None:
    """Return a document row with its nested version history, newest first."""
    response = (
        client.table("documents")
        .select(f"{DOCUMENT_COLUMNS}, document_versions(*)")
        .eq("document_id", str(document_id))
        .order("version_number", desc=True, foreign_table="document_versions")
        .maybe_single()
        .execute()
    )
    return response.data


def get_document_version(
    client: Client,
    document_version_id: UUID | str,
) -> dict | None:
    """Return a single document version row, or None when it does not exist."""
    response = (
        client.table("document_versions")
        .select(DOCUMENT_VERSION_COLUMNS)
        .eq("document_version_id", str(document_version_id))
        .maybe_single()
        .execute()
    )
    return response.data


def update_document_version_lifecycle(
    client: Client,
    document_version_id: UUID | str,
    lifecycle_status: str,
) -> None:
    """Move a document version to a new lifecycle status."""
    client.table("document_versions").update(
        {"lifecycle_status": lifecycle_status}
    ).eq("document_version_id", str(document_version_id)).execute()


def create_next_document_version(
    client: Client,
    payload: DocumentVersionCreate,
    created_by_user_id: UUID | str,
) -> dict:
    """Register the next version of an existing document.

    The new version number is one greater than the document's current highest
    version, the new row supersedes that current latest version, and the
    previous latest version's ``lifecycle_status`` is moved to ``superseded``.

    This helper is additive and does not modify the existing
    ``create_document_version`` function in ``app.repositories.ingestion``,
    which always writes version 1 for a brand-new document.
    """
    latest_response = (
        client.table("document_versions")
        .select("document_version_id, version_number, lifecycle_status")
        .eq("document_id", str(payload.document_id))
        .order("version_number", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    # maybe_single() returns None when no row matches (no versions yet); guard
    # the response before accessing .data (see Phase 4.2 repository pattern).
    latest = latest_response.data if latest_response is not None else None
    next_version_number = 1 if latest is None else int(latest["version_number"]) + 1

    row = payload.model_dump(mode="json")
    row.update(
        {
            "version_number": next_version_number,
            "storage_provider": STORAGE_PROVIDER,
            "lifecycle_status": "draft",
            "created_by_user_id": str(created_by_user_id),
        }
    )
    if latest is not None:
        row["supersedes_version_id"] = latest["document_version_id"]

    insert_response = client.table("document_versions").insert(row).execute()
    created = insert_response.data[0]

    if latest is not None and latest.get("lifecycle_status") != "superseded":
        update_document_version_lifecycle(
            client, latest["document_version_id"], "superseded"
        )

    return created


# ============================================================================
# FAQs
# ============================================================================


def list_faqs(
    client: Client,
    institution_id: UUID | None | str = None,
    category: str | None = None,
    include_inactive: bool = False,
    limit: int = 200,
) -> list[dict]:
    """List FAQs ordered by display order.

    When ``institution_id`` is None both global and per-institution FAQs are
    returned (the caller filters as needed).
    """
    query = client.table("faqs").select(FAQ_COLUMNS)
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    if category is not None:
        query = query.eq("category", category)
    if not include_inactive:
        query = query.eq("is_active", True)
    response = query.order("display_order").limit(limit).execute()
    return response.data


def get_faq(client: Client, faq_id: UUID | str) -> dict | None:
    """Return one FAQ row, or None when it does not exist."""
    response = (
        client.table("faqs")
        .select(FAQ_COLUMNS)
        .eq("faq_id", str(faq_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data


def create_faq(client: Client, payload: FaqCreate) -> dict:
    """Insert a new FAQ row and return it."""
    row = payload.model_dump(mode="json")
    response = client.table("faqs").insert(row).execute()
    return response.data[0]


def update_faq(client: Client, faq_id: UUID | str, payload: FaqUpdate) -> dict | None:
    """Apply a partial update to a FAQ and return the updated row."""
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise ValueError("FAQ update payload is empty")
    response = (
        client.table("faqs").update(fields).eq("faq_id", str(faq_id)).execute()
    )
    return response.data[0] if response.data else None


def delete_faq(client: Client, faq_id: UUID | str) -> None:
    """Delete a FAQ row."""
    client.table("faqs").delete().eq("faq_id", str(faq_id)).execute()


# ============================================================================
# Notices
# ============================================================================


def list_notices(
    client: Client,
    institution_id: UUID | None | str = None,
    category: str | None = None,
    include_inactive: bool = False,
    limit: int = 200,
) -> list[dict]:
    """List notices pinned-first, then by publication date (newest first)."""
    query = client.table("notices").select(NOTICE_COLUMNS)
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    if category is not None:
        query = query.eq("category", category)
    if not include_inactive:
        query = query.eq("is_active", True)
    response = (
        query.order("is_pinned", desc=True)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def get_notice(client: Client, notice_id: UUID | str) -> dict | None:
    """Return one notice row, or None when it does not exist."""
    response = (
        client.table("notices")
        .select(NOTICE_COLUMNS)
        .eq("notice_id", str(notice_id))
        .maybe_single()
        .execute()
    )
    return response.data


def create_notice(
    client: Client,
    payload: NoticeCreate,
    created_by_user_id: UUID | str | None = None,
) -> dict:
    """Insert a new notice row and return it."""
    row = payload.model_dump(mode="json")
    if created_by_user_id is not None:
        row["created_by"] = str(created_by_user_id)
    response = client.table("notices").insert(row).execute()
    return response.data[0]


def update_notice(
    client: Client,
    notice_id: UUID | str,
    payload: NoticeUpdate,
) -> dict | None:
    """Apply a partial update to a notice and return the updated row."""
    fields = payload.model_dump(mode="json", exclude_unset=True)
    if not fields:
        raise ValueError("notice update payload is empty")
    response = (
        client.table("notices")
        .update(fields)
        .eq("notice_id", str(notice_id))
        .execute()
    )
    return response.data[0] if response.data else None


def delete_notice(client: Client, notice_id: UUID | str) -> None:
    """Delete a notice row."""
    client.table("notices").delete().eq("notice_id", str(notice_id)).execute()