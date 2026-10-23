from .support import (
    AUTH_HEADERS,
    AppError,
    MagicMock,
    TENANT_A,
    USER_ID,
    _active_institution_authorization,
    _assert_no_leak,
    _auth,
    _envelope,
    _safe_filename,
    _validate,
    client,
    patch,
    pytest,
    uuid4,
)


def test_safe_filename_strips_traversal():
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("..\\..\\secret.txt") == "secret.txt"
    assert _safe_filename("/abs/path/doc.pdf") == "doc.pdf"
    assert _safe_filename("") == "upload"


def test_safe_filename_restricts_character_set():
    cleaned = _safe_filename("my report (final)!.pdf")
    assert "/" not in cleaned and "\\" not in cleaned
    assert ".." not in cleaned
    for char in cleaned:
        assert char.isalnum() or char in "._-"


def test_upload_validation_enforces_size_limit():
    from app.config import settings

    with pytest.raises(AppError) as exc:
        _validate(
            "big.pdf", "application/pdf", settings.max_upload_size_mb * 1024 * 1024 + 1
        )
    assert exc.value.code == "FILE_TOO_LARGE"
    assert exc.value.status_code == 413


def test_ingest_object_key_is_tenant_scoped_and_sanitized():
    import asyncio
    from app.services.knowledge import ingestion as ingestion_svc

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "knowledge_source_id": "ks-1",
        "institution_id": TENANT_A,
    }
    upload = MagicMock()
    upload.filename = "../../evil.pdf"
    upload.content_type = "application/pdf"

    async def _fake_read():
        return b"%PDF fake"

    upload.read = _fake_read
    with (
        patch.object(ingestion_svc, "get_admin_client", return_value=db),
        patch.object(ingestion_svc, "get_r2_client", return_value=MagicMock()),
        patch.object(ingestion_svc, "upload_file", return_value="k") as up_mock,
        patch.object(
            ingestion_svc, "create_document", return_value={"document_id": "doc-1"}
        ),
        patch.object(
            ingestion_svc,
            "create_document_version",
            return_value={"document_version_id": "dv-1"},
        ),
        patch.object(
            ingestion_svc,
            "create_processing_run",
            return_value={"processing_run_id": "run-1"},
        ),
    ):
        result = asyncio.run(
            ingestion_svc.ingest_document(
                file=upload, knowledge_source_id="ks-1", user_id=USER_ID
            )
        )
    key = result.storage_object_key
    assert key.startswith(f"{TENANT_A}/ks-1/")
    assert ".." not in key and "\\" not in key
    assert up_mock.call_args[0][2] == key


def test_extraction_failure_response_carries_no_internals():
    run_id = str(uuid4())
    run = {
        "processing_run_id": run_id,
        "status": "queued",
        "document_versions": {
            "document_version_id": str(uuid4()),
            "knowledge_source_id": "ks-1",
            "storage_bucket": "b",
            "storage_object_key": "k",
            "file_type": "pdf",
        },
    }
    with (
        _auth("admin", TENANT_A),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.get_processing_run_with_version",
            return_value=run,
        ),
        patch(
            "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
            return_value={"knowledge_source_id": "ks-1", "institution_id": TENANT_A},
        ),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch(
            "app.api.knowledge.ingestion.download_file", return_value=b"not a pdf %%%"
        ),
    ):
        r = client.post(f"/api/v1/documents/{run_id}/extract", headers=AUTH_HEADERS)
    assert r.status_code == 500
    error = _envelope(r)
    assert error["code"] == "EXTRACTION_FAILED"
    assert error["message"] == "Document processing failed during extraction"
    _assert_no_leak(r.text)


def test_malformed_embedding_is_422_not_500():
    from app.services.knowledge.retrieval import retrieve_chunks

    with pytest.raises(AppError) as exc:
        retrieve_chunks([0.0] * 8, institution_id=TENANT_A)
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_QUERY_EMBEDDING"


def test_failed_upload_compensates_orphaned_object():
    import asyncio
    from app.services.knowledge import ingestion as ingestion_svc

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "knowledge_source_id": "ks-1",
        "institution_id": TENANT_A,
    }
    upload = MagicMock()
    upload.filename = "doc.pdf"
    upload.content_type = "application/pdf"

    async def _fake_read():
        return b"%PDF fake"

    upload.read = _fake_read
    with (
        patch.object(ingestion_svc, "get_admin_client", return_value=db),
        patch.object(ingestion_svc, "get_r2_client", return_value=MagicMock()),
        patch.object(ingestion_svc, "upload_file", return_value="k"),
        patch.object(
            ingestion_svc, "create_document", return_value={"document_id": "d"}
        ),
        patch.object(
            ingestion_svc,
            "create_document_version",
            side_effect=RuntimeError("db down"),
        ),
        patch.object(ingestion_svc, "delete_file") as del_mock,
    ):
        with pytest.raises(AppError) as exc:
            asyncio.run(
                ingestion_svc.ingest_document(
                    file=upload, knowledge_source_id="ks-1", user_id=USER_ID
                )
            )
    assert exc.value.code == "REGISTRATION_FAILED"
    del_mock.assert_called_once()


def test_embedding_failure_message_redacts_api_key():
    from app.services.knowledge.embeddings import _safe_error_message

    with patch("app.services.knowledge.embeddings.settings") as ms:
        ms.openrouter_api_key = "sk-or-SECRETVALUE"
        cleaned = _safe_error_message(Exception("boom sk-or-SECRETVALUE end"))
    assert "sk-or-SECRETVALUE" not in cleaned
    assert "[redacted]" in cleaned
