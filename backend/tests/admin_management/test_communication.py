from .support import (
    FAQ_ID,
    INSTITUTION_ID,
    MagicMock,
    NOTICE_ID,
    _audit_db,
    _audit_rows,
    _faq_row,
    admin_auth,
    client,
    patch,
)


def test_create_faq_endpoint_defers_rag_until_publish_and_audits() -> None:
    faq = _faq_row()
    db = _audit_db(first_insert=faq)
    with (
        patch("app.services.admin.admin_faq.get_admin_client", return_value=db),
        patch("app.services.admin.admin_faq.sync_canonical_text_record") as sync_mock,
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/faqs",
            json={
                "institution_id": INSTITUTION_ID,
                "question": faq["question"],
                "answer": faq["answer"],
            },
        )

    assert response.status_code == 201
    sync_mock.assert_not_called()
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.create"


def test_update_faq_deactivation_removes_retrievable_content() -> None:
    db = _audit_db()
    updated = _faq_row() | {"is_active": False}
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[updated])
    )
    get_faq_mock = MagicMock(return_value=_faq_row())
    with (
        patch("app.services.admin.admin_faq.get_admin_client", return_value=db),
        patch("app.repositories.admin.admin_knowledge.get_faq", get_faq_mock),
        patch("app.services.admin.admin_faq.sync_canonical_text_record") as sync_mock,
        patch(
            "app.services.admin.admin_faq.remove_canonical_text_record"
        ) as remove_mock,
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.patch(
            f"/api/v1/admin/faqs/{FAQ_ID}", json={"is_active": False}
        )

    assert response.status_code == 200
    sync_mock.assert_not_called()
    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.update"


def test_delete_faq_endpoint_removes_rag_content_and_audits() -> None:
    db = _audit_db()
    with (
        patch("app.services.admin.admin_faq.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin.admin_knowledge.get_faq",
            return_value=_faq_row(),
        ),
        patch(
            "app.services.admin.admin_faq.remove_canonical_text_record"
        ) as remove_mock,
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.delete(f"/api/v1/admin/faqs/{FAQ_ID}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    remove_mock.assert_called_once_with(f"faq:{FAQ_ID}", client=db)
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "faq.delete"


def test_create_notice_endpoint_defers_rag_until_publish_and_audits() -> None:
    notice = {
        "notice_id": NOTICE_ID,
        "institution_id": INSTITUTION_ID,
        "title": "Exam schedule",
        "content": "Midterms start Monday.",
        "category": "exam",
        "priority": "high",
        "is_active": True,
    }
    db = _audit_db(first_insert=notice)
    with (
        patch("app.services.admin.admin_notices.get_admin_client", return_value=db),
        patch(
            "app.services.admin.admin_notices.sync_canonical_text_record"
        ) as sync_mock,
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/notices",
            json={
                "institution_id": INSTITUTION_ID,
                "title": notice["title"],
                "content": notice["content"],
                "category": "exam",
                "priority": "high",
            },
        )

    assert response.status_code == 201
    sync_mock.assert_not_called()
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "notice.create"
