from .support import (
    ADMIN_USER,
    AsyncMock,
    DOC_ID,
    INSTITUTION_ID,
    KS_ID,
    MagicMock,
    _audit_db,
    _audit_rows,
    admin_auth,
    client,
    patch,
    uuid4,
)


def test_create_knowledge_source_audits_mutation() -> None:
    db = _audit_db(first_insert={"knowledge_source_id": KS_ID})
    with patch("app.api.admin.common.get_admin_client", return_value=db):
        response = client.post(
            "/api/v1/admin/knowledge-sources",
            json={
                "institution_id": INSTITUTION_ID,
                "source_type": "handbook",
                "title": "Student Handbook",
            },
        )

    assert response.status_code == 201
    assert response.json()["knowledge_source_id"] == KS_ID
    tables = [call.args[0] for call in db.table.call_args_list]
    assert "knowledge_sources" in tables
    assert "admin_audit_log" in tables
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "knowledge_source.create"
    assert audit_rows[0]["actor_user_id"] == ADMIN_USER["user_id"]


def test_update_knowledge_source_404_when_missing() -> None:
    db = _audit_db()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    with (
        patch("app.api.admin.common.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin.admin_knowledge.get_knowledge_source_detail",
            return_value=None,
        ),
    ):
        response = client.patch(
            f"/api/v1/admin/knowledge-sources/{KS_ID}", json={"title": "New"}
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"


def test_document_upload_endpoint_orchestrates_and_audits() -> None:
    upload_result = {
        "document_id": DOC_ID,
        "document_version_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "status": "embedded",
    }
    db = _audit_db()
    with (
        patch(
            "app.services.admin.admin_documents.upload_document",
            new=AsyncMock(return_value=upload_result),
        ),
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.post(
            "/api/v1/admin/documents",
            files={"file": ("handbook.pdf", b"pdf-bytes", "application/pdf")},
            data={"knowledge_source_id": KS_ID, "auto_process": "true"},
        )

    assert response.status_code == 201
    assert response.json()["document_id"] == DOC_ID
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.upload"


def test_document_version_endpoint_uses_versioning_and_audits() -> None:
    version_result = {
        "document_id": DOC_ID,
        "document_version_id": str(uuid4()),
        "version_number": 2,
        "supersedes_version_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "status": "queued",
    }
    db = _audit_db()
    with (
        patch(
            "app.services.admin.admin_documents.update_document",
            new=AsyncMock(return_value=version_result),
        ),
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.post(
            f"/api/v1/admin/documents/{DOC_ID}/versions",
            files={"file": ("handbook-v2.pdf", b"pdf-bytes-2", "application/pdf")},
            data={"auto_process": "false"},
        )

    assert response.status_code == 201
    assert response.json()["version_number"] == 2
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.update"
    assert audit_rows[0]["record_id"] == DOC_ID


def test_document_delete_endpoint_audits() -> None:
    db = _audit_db()
    with (
        patch(
            "app.services.admin.admin_documents.delete_document",
            return_value={"deleted": True, "document_id": DOC_ID},
        ),
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        response = client.delete(f"/api/v1/admin/documents/{DOC_ID}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    audit_rows = [r for r in _audit_rows(db) if "action" in r]
    assert audit_rows[0]["action"] == "document.delete"
