"""Admin FAQ service (Phase Admin-3).

CRUD over the ``faqs`` table plus RAG synchronization: the database record is
the source of truth and its rendered canonical text is stored/synced through
the existing document/version/processing pipeline (see
``app.services.admin_documents.sync_canonical_text_record``). Deactivating or
deleting a FAQ removes its retrievable content so nothing stale remains.
"""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_knowledge as knowledge_repo
from app.schemas.admin import FaqCreate, FaqUpdate
from app.services.admin_documents import (
    remove_canonical_text_record,
    sync_canonical_text_record,
)

FAQ_SOURCE_TYPE = "faq"
FAQ_KS_TITLE = "Frequently Asked Questions"


def faq_marker(faq_id: UUID | str) -> str:
    """The version-label marker that links a FAQ to its synthetic document."""
    return f"faq:{faq_id}"


def render_faq_canonical_text(faq: dict) -> str:
    """Render the canonical retrieval text for a FAQ record."""
    category = (faq.get("category") or "general").strip()
    question = (faq.get("question") or "").strip()
    answer = (faq.get("answer") or "").strip()
    return f"FAQ [{category}] {question}\n{answer}"


def _sync_faq(faq: dict, actor_user_id: UUID | str) -> None:
    try:
        sync_canonical_text_record(
            institution_id=faq.get("institution_id"),
            source_type=FAQ_SOURCE_TYPE,
            knowledge_source_title=FAQ_KS_TITLE,
            marker=faq_marker(faq["faq_id"]),
            canonical_text=render_faq_canonical_text(faq),
            actor_user_id=actor_user_id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "FAQ RAG synchronization failed",
            status_code=500,
            code="RAG_SYNC_FAILED",
        ) from exc


def list_faqs(
    institution_id: UUID | str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    limit: int = 200,
) -> list[dict]:
    db = get_admin_client()
    return knowledge_repo.list_faqs(
        db,
        institution_id=institution_id,
        category=category,
        include_inactive=include_inactive,
        limit=limit,
    )


def get_faq(faq_id: UUID | str) -> dict:
    db = get_admin_client()
    faq = knowledge_repo.get_faq(db, faq_id)
    if faq is None:
        raise AppError("FAQ not found", status_code=404, code="FAQ_NOT_FOUND")
    return faq


def create_faq(payload: FaqCreate, actor_user_id: UUID | str) -> dict:
    """Create the FAQ record (source of truth), then sync it into the RAG store."""
    db = get_admin_client()
    faq = knowledge_repo.create_faq(db, payload)
    _sync_faq(faq, actor_user_id)
    return faq


def update_faq(faq_id: UUID | str, payload: FaqUpdate, actor_user_id: UUID | str) -> dict:
    """Update the FAQ record, then re-sync or retire its retrieval content."""
    db = get_admin_client()
    if knowledge_repo.get_faq(db, faq_id) is None:
        raise AppError("FAQ not found", status_code=404, code="FAQ_NOT_FOUND")
    updated = knowledge_repo.update_faq(db, faq_id, payload)
    if updated is None:
        raise AppError("FAQ not found", status_code=404, code="FAQ_NOT_FOUND")

    if updated.get("is_active") is False:
        # Deactivated FAQs must not remain retrievable.
        remove_canonical_text_record(faq_marker(faq_id), client=db)
    else:
        _sync_faq(updated, actor_user_id)
    return updated


def delete_faq(faq_id: UUID | str) -> dict:
    """Delete the FAQ record and remove its retrievable content."""
    db = get_admin_client()
    existing = knowledge_repo.get_faq(db, faq_id)
    if existing is None:
        raise AppError("FAQ not found", status_code=404, code="FAQ_NOT_FOUND")
    knowledge_repo.delete_faq(db, faq_id)
    remove_canonical_text_record(faq_marker(faq_id), client=db)
    return existing


def publish_faq(faq_id: UUID | str, actor_user_id: UUID | str) -> dict:
    """Publish a FAQ and sync its canonical text into the RAG store."""
    db = get_admin_client()
    faq = knowledge_repo.get_faq(db, faq_id)
    if faq is None:
        raise AppError("FAQ not found", status_code=404, code="FAQ_NOT_FOUND")
    db.table("faqs").update({"is_published": True}).eq("faq_id", str(faq_id)).execute()
    updated = knowledge_repo.get_faq(db, faq_id)
    _sync_faq(updated, actor_user_id)
    return updated
