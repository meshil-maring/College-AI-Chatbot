"""Test knowledge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest

from .support import (
    ADMIN_A_USER,
    INST_B,
    RESOURCE_ID,
    _authenticated,
    _clean_dependencies,
    authorized_admin_endpoint,
    client,
    conflicting_admin,
)


def test_cross_tenant_knowledge_source_and_document_are_denied(
    authorized_admin_endpoint,
) -> None:
    foreign_source = {"knowledge_source_id": RESOURCE_ID, "institution_id": INST_B}
    document = {"document_id": RESOURCE_ID, "knowledge_source_id": RESOURCE_ID}
    with (
        patch(
            "app.repositories.admin.admin_knowledge.get_document_with_versions",
            return_value=document,
        ) as get_document,
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value=foreign_source,
        ) as get_source,
    ):
        response = client.get(f"/api/v1/admin/documents/{RESOURCE_ID}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    get_document.assert_called_once_with(authorized_admin_endpoint, UUID(RESOURCE_ID))
    get_source.assert_called_once_with(authorized_admin_endpoint, RESOURCE_ID)


def test_unknown_knowledge_source_is_denied_with_not_found(
    authorized_admin_endpoint,
) -> None:
    with (
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value=None,
        ) as get_source,
        patch(
            "app.repositories.admin.admin_knowledge.list_documents_for_source",
            return_value=[],
        ) as listing,
    ):
        response = client.get(
            f"/api/v1/admin/knowledge-sources/{RESOURCE_ID}/documents"
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"
    get_source.assert_called_once_with(authorized_admin_endpoint, UUID(RESOURCE_ID))
    listing.assert_not_called()


@pytest.mark.parametrize(
    ("method", "path", "service_name", "row"),
    [
        (
            "PATCH",
            f"/api/v1/admin/faqs/{RESOURCE_ID}",
            "admin_faq.get_faq",
            {"faq_id": RESOURCE_ID, "institution_id": INST_B},
        ),
        (
            "DELETE",
            f"/api/v1/admin/notices/{RESOURCE_ID}",
            "admin_notices.get_notice",
            {"notice_id": RESOURCE_ID, "institution_id": INST_B},
        ),
    ],
)
def test_cross_tenant_faq_and_notice_mutations_are_denied(
    method: str, path: str, service_name: str, row: dict
) -> None:
    payload = {"question": "changed"} if method == "PATCH" else None
    with (
        _authenticated(ADMIN_A_USER),
        patch(f"app.services.admin.{service_name}", return_value=row),
    ):
        response = client.request(method, path, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_global_faq_mutation_is_not_tenant_admin_authority() -> None:
    with (
        _authenticated(ADMIN_A_USER),
        patch(
            "app.services.admin.admin_faq.get_faq",
            return_value={"faq_id": RESOURCE_ID, "institution_id": None},
        ),
    ):
        response = client.patch(
            f"/api/v1/admin/faqs/{RESOURCE_ID}", json={"question": "changed"}
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
