from .support import (
    AUTH_HEADERS,
    INSTITUTION_B,
    _active_institution_authorization,
    _auth,
    client,
    patch,
)


def test_cross_tenant_notice_and_faq_mutations_write_nothing():
    notice_payload = {
        "institution_id": INSTITUTION_B,
        "title": "Foreign notice",
        "content": "Should never be created.",
    }
    faq_payload = {
        "institution_id": INSTITUTION_B,
        "question": "Foreign FAQ?",
        "answer": "Should never be created.",
    }

    with (
        _auth("admin"),
        patch("app.services.admin.admin_notices.create_notice") as write_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
    ):
        response = client.post(
            "/api/v1/admin/notices", json=notice_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()

    with (
        _auth("admin"),
        patch("app.services.admin.admin_faq.create_faq") as write_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
    ):
        response = client.post(
            "/api/v1/admin/faqs", json=faq_payload, headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()
    audit_mock.assert_not_called()
