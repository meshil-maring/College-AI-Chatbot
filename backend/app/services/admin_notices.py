"""Admin notice service (Phase Admin-3).

CRUD over the ``notices`` table plus RAG synchronization: the database record
is the source of truth and its rendered canonical text is stored/synced
through the existing document/version/processing pipeline (see
``app.services.admin_documents.sync_canonical_text_record``). Deactivating or
deleting a notice removes its retrievable content so nothing stale remains.
"""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_knowledge as knowledge_repo
from app.schemas.admin import NoticeCreate, NoticeUpdate
from app.services.admin_documents import (
    remove_canonical_text_record,
    sync_canonical_text_record,
)

NOTICE_SOURCE_TYPE = "notice"
NOTICE_KS_TITLE = "Notices and Announcements"


def notice_marker(notice_id: UUID | str) -> str:
    """The version-label marker that links a notice to its synthetic document."""
    return f"notice:{notice_id}"


def render_notice_canonical_text(notice: dict) -> str:
    """Render the canonical retrieval text for a notice record."""
    category = (notice.get("category") or "general").strip()
    priority = (notice.get("priority") or "normal").strip()
    title = (notice.get("title") or "").strip()
    content = (notice.get("content") or "").strip()
    return f"NOTICE [{category}|priority:{priority}] {title}\n{content}"


def _sync_notice(notice: dict, actor_user_id: UUID | str) -> None:
    try:
        sync_canonical_text_record(
            institution_id=notice.get("institution_id"),
            source_type=NOTICE_SOURCE_TYPE,
            knowledge_source_title=NOTICE_KS_TITLE,
            marker=notice_marker(notice["notice_id"]),
            canonical_text=render_notice_canonical_text(notice),
            actor_user_id=actor_user_id,
        )
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "Notice RAG synchronization failed",
            status_code=500,
            code="RAG_SYNC_FAILED",
        ) from exc


def list_notices(
    institution_id: UUID | str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    limit: int = 200,
) -> list[dict]:
    db = get_admin_client()
    return knowledge_repo.list_notices(
        db,
        institution_id=institution_id,
        category=category,
        include_inactive=include_inactive,
        limit=limit,
    )


def get_notice(notice_id: UUID | str) -> dict:
    db = get_admin_client()
    notice = knowledge_repo.get_notice(db, notice_id)
    if notice is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")
    return notice


def create_notice(payload: NoticeCreate, actor_user_id: UUID | str) -> dict:
    """Create the notice record (source of truth), then sync it into the RAG store."""
    db = get_admin_client()
    notice = knowledge_repo.create_notice(db, payload, created_by_user_id=actor_user_id)
    _sync_notice(notice, actor_user_id)
    return notice


def update_notice(
    notice_id: UUID | str,
    payload: NoticeUpdate,
    actor_user_id: UUID | str,
) -> dict:
    """Update the notice record, then re-sync or retire its retrieval content."""
    db = get_admin_client()
    if knowledge_repo.get_notice(db, notice_id) is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")
    updated = knowledge_repo.update_notice(db, notice_id, payload)
    if updated is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")

    if updated.get("is_active") is False:
        # Deactivated notices must not remain retrievable.
        remove_canonical_text_record(notice_marker(notice_id), client=db)

    else:
        _sync_notice(updated, actor_user_id)
    return updated


def publish_notice(notice_id: UUID | str, actor_user_id: UUID | str) -> dict:
    """Publish a notice and sync its canonical text into the RAG store."""
    db = get_admin_client()
    notice = knowledge_repo.get_notice(db, notice_id)
    if notice is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")
    db.table("notices").update({"is_published": True}).eq("notice_id", str(notice_id)).execute()
    updated = knowledge_repo.get_notice(db, notice_id)
    _sync_notice(updated, actor_user_id)
    return updated


def unpublish_notice(notice_id: UUID | str, actor_user_id: UUID | str) -> dict:
    """Unpublish a notice and retire its retrievable content."""
    db = get_admin_client()
    notice = knowledge_repo.get_notice(db, notice_id)
    if notice is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")
    db.table("notices").update({"is_published": False}).eq("notice_id", str(notice_id)).execute()
    updated = knowledge_repo.get_notice(db, notice_id)
    remove_canonical_text_record(notice_marker(notice_id), client=db)
    return updated


def delete_notice(notice_id: UUID | str) -> dict:
    """Delete the notice record and remove its retrievable content."""
    db = get_admin_client()
    existing = knowledge_repo.get_notice(db, notice_id)
    if existing is None:
        raise AppError("Notice not found", status_code=404, code="NOTICE_NOT_FOUND")
    knowledge_repo.delete_notice(db, notice_id)
    remove_canonical_text_record(notice_marker(notice_id), client=db)
    return existing
