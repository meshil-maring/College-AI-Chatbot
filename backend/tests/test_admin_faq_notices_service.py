"""Phase Admin-3 tests — FAQ and notice RAG synchronization services.

The database record is the source of truth; canonical text is rendered from
it and synced through the document/version/processing pipeline. Deletes and
deactivations remove retrievable content.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services import admin_faq, admin_notices
from app.schemas.admin import FaqCreate, FaqUpdate, NoticeCreate, NoticeUpdate

FAQ_ID = str(uuid4())
NOTICE_ID = str(uuid4())
ACTOR = "70000000-0000-0000-0000-000000000001"
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"


def _faq(**overrides) -> dict:
    row = {
        "faq_id": FAQ_ID,
        "institution_id": INSTITUTION_ID,
        "category": "general",
        "question": "What are the library hours?",
        "answer": "8am to 10pm on weekdays.",
        "display_order": 0,
        "is_active": True,
    }
    row.update(overrides)
    return row


def _notice(**overrides) -> dict:
    row = {
        "notice_id": NOTICE_ID,
        "institution_id": INSTITUTION_ID,
        "title": "Exam schedule",
        "content": "Midterms start Monday.",
        "category": "exam",
        "priority": "high",
        "is_active": True,
        "is_pinned": False,
    }
    row.update(overrides)
    return row


# ============================================================================
# FAQ
# ============================================================================


def test_faq_canonical_text_renders_category_question_answer() -> None:
    text = admin_faq.render_faq_canonical_text(_faq())
    assert text == "FAQ [general] What are the library hours?\n8am to 10pm on weekdays."


def test_faq_marker_includes_type_prefix() -> None:
    assert admin_faq.faq_marker(FAQ_ID) == f"faq:{FAQ_ID}"


def test_create_faq_persists_record_then_syncs_rag() -> None:
    db = MagicMock()
    faq = _faq()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.create_faq", return_value=faq),
        patch("app.services.admin_faq.sync_canonical_text_record") as sync_mock,
    ):
        result = admin_faq.create_faq(
            FaqCreate(institution_id=uuid4(), question="Q?", answer="A"), ACTOR
        )

    assert result == faq
    sync_mock.assert_called_once()
    kwargs = sync_mock.call_args.kwargs
    assert kwargs["marker"] == f"faq:{FAQ_ID}"
    assert kwargs["source_type"] == "faq"
    assert kwargs["actor_user_id"] == ACTOR
    assert faq["question"] in kwargs["canonical_text"]


def test_create_faq_wraps_sync_failure() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.create_faq", return_value=_faq()),
        patch(
            "app.services.admin_faq.sync_canonical_text_record",
            side_effect=RuntimeError("pipeline down"),
        ),
    ):
        with pytest.raises(AppError) as exc:
            admin_faq.create_faq(FaqCreate(question="Q?", answer="A"), ACTOR)
    assert exc.value.code == "RAG_SYNC_FAILED"

def test_update_faq_reactivates_with_resync() -> None:
    db = MagicMock()
    updated = _faq(answer="Updated answer")
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", return_value=_faq()),
        patch("app.repositories.admin_knowledge.update_faq", return_value=updated),
        patch("app.services.admin_faq.sync_canonical_text_record") as sync_mock,
    ):
        result = admin_faq.update_faq(FAQ_ID, FaqUpdate(answer="Updated answer"), ACTOR)

    assert result == updated
    sync_mock.assert_called_once()
    assert updated["answer"] in sync_mock.call_args.kwargs["canonical_text"]


def test_update_faq_deactivation_removes_retrievable_content() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", return_value=_faq()),
        patch(
            "app.repositories.admin_knowledge.update_faq",
            return_value=_faq(is_active=False),
        ),
        patch(
            "app.services.admin_faq.remove_canonical_text_record", return_value=True
        ) as remove_mock,
        patch("app.services.admin_faq.sync_canonical_text_record") as sync_mock,
    ):
        admin_faq.update_faq(FAQ_ID, FaqUpdate(is_active=False), ACTOR)

    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)
    sync_mock.assert_not_called()


def test_update_faq_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            admin_faq.update_faq(FAQ_ID, FaqUpdate(answer="x"), ACTOR)
    assert exc.value.status_code == 404


def test_delete_faq_removes_record_and_rag_content() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", return_value=_faq()),
        patch("app.repositories.admin_knowledge.delete_faq") as delete_mock,
        patch(
            "app.services.admin_faq.remove_canonical_text_record", return_value=True
        ) as remove_mock,
    ):
        result = admin_faq.delete_faq(FAQ_ID)

    assert result["faq_id"] == FAQ_ID
    delete_mock.assert_called_once_with(db, FAQ_ID)
    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)


def test_delete_faq_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_faq", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            admin_faq.delete_faq(FAQ_ID)
    assert exc.value.status_code == 404

# ============================================================================
# Notices
# ============================================================================


def test_notice_canonical_text_renders_category_priority_title_content() -> None:
    text = admin_notices.render_notice_canonical_text(_notice())
    assert text == (
        "NOTICE [exam|priority:high] Exam schedule\nMidterms start Monday."
    )


def test_notice_marker_includes_type_prefix() -> None:
    assert admin_notices.notice_marker(NOTICE_ID) == f"notice:{NOTICE_ID}"


def test_create_notice_persists_record_then_syncs_rag() -> None:
    db = MagicMock()
    notice = _notice()
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_knowledge.create_notice", return_value=notice
        ) as create_mock,
        patch("app.services.admin_notices.sync_canonical_text_record") as sync_mock,
    ):
        result = admin_notices.create_notice(
            NoticeCreate(title="Exam schedule", content="Midterms start Monday."), ACTOR
        )

    assert result == notice
    create_mock.assert_called_once()
    sync_mock.assert_called_once()
    kwargs = sync_mock.call_args.kwargs
    assert kwargs["marker"] == f"notice:{NOTICE_ID}"
    assert kwargs["source_type"] == "notice"
    assert notice["title"] in kwargs["canonical_text"]
    assert notice["content"] in kwargs["canonical_text"]


def test_update_notice_deactivation_removes_retrievable_content() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_notice", return_value=_notice()),
        patch(
            "app.repositories.admin_knowledge.update_notice",
            return_value=_notice(is_active=False),
        ),
        patch(
            "app.services.admin_notices.remove_canonical_text_record",
            return_value=True,
        ) as remove_mock,
        patch("app.services.admin_notices.sync_canonical_text_record") as sync_mock,
    ):
        admin_notices.update_notice(
            NOTICE_ID, NoticeUpdate(is_active=False), ACTOR
        )

    remove_mock.assert_called_once_with(f"notice:{NOTICE_ID}", client=db)
    sync_mock.assert_not_called()


def test_update_notice_resyncs_on_content_change() -> None:
    db = MagicMock()
    updated = _notice(content="Midterms moved to Tuesday.")
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_notice", return_value=_notice()),
        patch("app.repositories.admin_knowledge.update_notice", return_value=updated),
        patch("app.services.admin_notices.sync_canonical_text_record") as sync_mock,
    ):
        admin_notices.update_notice(
            NOTICE_ID, NoticeUpdate(content="Midterms moved to Tuesday."), ACTOR
        )

    sync_mock.assert_called_once()
    assert "Tuesday" in sync_mock.call_args.kwargs["canonical_text"]


def test_delete_notice_removes_record_and_rag_content() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_notice", return_value=_notice()),
        patch("app.repositories.admin_knowledge.delete_notice") as delete_mock,
        patch(
            "app.services.admin_notices.remove_canonical_text_record",
            return_value=True,
        ) as remove_mock,
    ):
        result = admin_notices.delete_notice(NOTICE_ID)

    assert result["notice_id"] == NOTICE_ID
    delete_mock.assert_called_once_with(db, NOTICE_ID)
    remove_mock.assert_called_once_with(f"notice:{NOTICE_ID}", client=db)


def test_delete_notice_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.admin_notices.get_admin_client", return_value=db),
        patch("app.repositories.admin_knowledge.get_notice", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            admin_notices.delete_notice(NOTICE_ID)
    assert exc.value.status_code == 404


