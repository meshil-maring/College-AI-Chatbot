from .support import (
    AUTH_HEADERS,
    FAQ_B,
    INSTITUTION_B,
    KNOWLEDGE_SOURCE_B,
    MagicMock,
    NOTICE_B,
    RESULT_B,
    _active_institution_authorization,
    _assert_tenant_mismatch,
    _auth,
    client,
    patch,
)


def test_admin_a_cannot_read_admin_b_notice_faq_document_and_knowledge_source():
    """Every admin read surface re-checks the row's tenant (not just the query)."""
    with (
        _auth("admin"),
        patch(
            "app.services.admin.admin_notices.get_notice",
            return_value={"notice_id": NOTICE_B, "institution_id": INSTITUTION_B},
        ),
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/notices/{NOTICE_B}")

    with (
        _auth("admin"),
        patch(
            "app.services.admin.admin_faq.get_faq",
            return_value={"faq_id": FAQ_B, "institution_id": INSTITUTION_B},
        ),
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/faqs/{FAQ_B}")

    with (
        _auth("admin"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value={
                "knowledge_source_id": KNOWLEDGE_SOURCE_B,
                "institution_id": INSTITUTION_B,
            },
        ),
    ):
        _assert_tenant_mismatch(
            "admin", "GET", f"/api/v1/admin/knowledge-sources/{KNOWLEDGE_SOURCE_B}"
        )

    with (
        _auth("admin"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.admin.admin_knowledge.get_document_with_versions",
            return_value={
                "document_id": RESULT_B,
                "knowledge_source_id": KNOWLEDGE_SOURCE_B,
            },
        ),
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value={
                "knowledge_source_id": KNOWLEDGE_SOURCE_B,
                "institution_id": INSTITUTION_B,
            },
        ),
    ):
        _assert_tenant_mismatch("admin", "GET", f"/api/v1/admin/documents/{RESULT_B}")


def test_cross_tenant_knowledge_source_and_document_writes_create_nothing():
    with (
        _auth("admin"),
        patch(
            "app.repositories.admin.admin_knowledge.create_knowledge_source"
        ) as create_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
        patch("app.api.admin.common.get_admin_client") as db_mock,
    ):
        response = client.post(
            "/api/v1/admin/knowledge-sources",
            json={
                "institution_id": INSTITUTION_B,
                "source_type": "document",
                "title": "Foreign source",
            },
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    create_mock.assert_not_called()
    audit_mock.assert_not_called()
    db_mock.assert_not_called()

    # Uploading a document into another institution's knowledge source.
    with (
        _auth("admin"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value={
                "knowledge_source_id": KNOWLEDGE_SOURCE_B,
                "institution_id": INSTITUTION_B,
            },
        ),
        patch("app.services.admin.admin_documents.upload_document") as upload_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
    ):
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("notes.txt", b"foreign content", "text/plain")},
            data={"knowledge_source_id": KNOWLEDGE_SOURCE_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    upload_mock.assert_not_called()
    audit_mock.assert_not_called()
