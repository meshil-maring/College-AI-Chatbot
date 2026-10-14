"""Document processing requires verified ownership before content or state access."""

from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import ingestion
from app.core.security import get_current_user
from app.main import app


INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
FOREIGN_INSTITUTION_ID = "30000000-0000-0000-0000-000000000002"
USER_ID = "30000000-0000-0000-0000-000000000101"
SOURCE_ID = "30000000-0000-0000-0000-000000000201"
VERSION_ID = "d0000000-0000-0000-0000-000000000003"
RUN_ID = "a0000000-0000-0000-0000-000000000003"
SOURCE = {"knowledge_source_id": SOURCE_ID, "institution_id": INSTITUTION_ID}
RUN = {
    "processing_run_id": RUN_ID,
    "status": "ready",
    "document_version_id": VERSION_ID,
    "document_versions": {
        "document_version_id": VERSION_ID,
        "knowledge_source_id": SOURCE_ID,
        "storage_bucket": "test-bucket",
        "storage_object_key": "test/document.txt",
        "file_type": "txt",
    },
}
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(params=["admin", "staff", "faculty"])
def processing(request):
    role = request.param
    principal = {
        "user_id": USER_ID,
        "roles": [role],
        "status": "active",
        # The real dependency must pin this to the authoritative grant.
        "institution_id": None,
        "role_assignments": [{
            "role": role, "scope_type": "institution",
            "scope_id": INSTITUTION_ID, "is_active": True,
        }],
    }
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: principal
    try:
        with ExitStack() as stack:
            db = MagicMock()
            stack.enter_context(patch("app.services.authorization.get_admin_client", return_value=db))
            stack.enter_context(patch(
                "app.services.authorization.tenancy_repo.get_institution_by_id",
                return_value={"status": "active", "is_active": True},
            ))
            stack.enter_context(patch.object(ingestion, "get_admin_client", return_value=db))
            source = stack.enter_context(patch.object(ingestion, "get_knowledge_source", return_value=deepcopy(SOURCE)))
            detail = stack.enter_context(patch.object(ingestion.knowledge_repo, "get_knowledge_source_detail", return_value=deepcopy(SOURCE)))
            run = stack.enter_context(patch.object(ingestion, "get_processing_run_with_version", return_value=deepcopy(RUN)))
            effects = {
                name: stack.enter_context(patch.object(ingestion, name))
                for name in (
                    "get_r2_client", "download_file", "get_extracted_text",
                    "update_run_status", "store_extracted_text", "delete_chunks_for_run",
                    "insert_chunks", "extract_text", "chunk_text", "embed_processing_run",
                )
            }
            effects["ingest_document"] = stack.enter_context(patch.object(ingestion, "ingest_document", new_callable=AsyncMock))
            effects["ingest_document"].return_value = {
                "knowledge_source_id": SOURCE_ID, "document_id": SOURCE_ID,
                "document_version_id": VERSION_ID, "processing_run_id": RUN_ID,
                "storage_object_key": "test/document.txt", "status": "queued",
            }
            yield {"db": db, "source": source, "detail": detail, "run": run, "effects": effects}
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def _request(operation, *, source_id=SOURCE_ID):
    if operation == "ingest":
        return client.post(
            "/api/v1/documents/ingest",
            data={"knowledge_source_id": source_id} if source_id is not None else {},
            files={"file": ("document.txt", b"test content", "text/plain")},
        )
    return client.post(f"/api/v1/documents/{RUN_ID}/{operation}")


def _assert_no_processing(processing):
    for mock in processing["effects"].values():
        mock.assert_not_called()
    processing["db"].table.assert_not_called()
    processing["db"].rpc.assert_not_called()


@pytest.mark.parametrize("operation", ["ingest", "extract", "chunk", "embed"])
@pytest.mark.parametrize("ownership", ["missing-source", "missing-institution", "null-owner", "foreign-owner"])
def test_unverified_source_rejects_before_processing(processing, operation, ownership):
    source = deepcopy(SOURCE)
    if ownership == "missing-source":
        source = None
    elif ownership == "missing-institution":
        source.pop("institution_id")
    else:
        source["institution_id"] = None if ownership == "null-owner" else FOREIGN_INSTITUTION_ID
    processing["source"].return_value = source
    processing["detail"].return_value = source
    processing["run"].return_value["status"] = "queued" if operation == "extract" else "ready"

    response = _request(operation)

    assert response.status_code == (404 if ownership == "missing-source" else 403)
    assert response.json()["error"]["code"] == (
        "KNOWLEDGE_SOURCE_NOT_FOUND" if ownership == "missing-source" else "TENANT_MISMATCH"
    )
    _assert_no_processing(processing)


@pytest.mark.parametrize("operation", ["extract", "chunk", "embed"])
@pytest.mark.parametrize("relationship", ["missing-version", "null-version", "missing-document", "missing-source-id", "null-source-id"])
def test_missing_run_relationship_rejects_before_processing(processing, operation, relationship):
    run = processing["run"].return_value
    run["status"] = "queued" if operation == "extract" else "ready"
    if relationship == "missing-version":
        run.pop("document_versions")
    elif relationship == "null-version":
        run["document_versions"] = None
    elif relationship == "null-source-id":
        run["document_versions"]["knowledge_source_id"] = None
    else:
        run["document_versions"].pop("knowledge_source_id")
        run["document_versions"]["documents"] = None if relationship == "missing-document" else {}

    response = _request(operation)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"
    processing["detail"].assert_not_called()
    _assert_no_processing(processing)


@pytest.mark.parametrize("operation", ["extract", "chunk", "embed"])
def test_foreign_run_states_have_identical_rejections(processing, operation):
    processing["detail"].return_value["institution_id"] = FOREIGN_INSTITUTION_ID
    responses = []
    for status in ("queued", "ready", "processing", "failed"):
        processing["run"].return_value["status"] = status
        response = _request(operation)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"
        responses.append(response.json())
        _assert_no_processing(processing)
    assert all(body == responses[0] for body in responses)


@pytest.mark.parametrize("source_id", [None, "", " "])
def test_ingest_requires_source_id_before_processing(processing, source_id):
    response = _request("ingest", source_id=source_id)
    assert response.status_code in (404, 422)
    processing["source"].assert_not_called()
    _assert_no_processing(processing)


@pytest.mark.parametrize("operation", ["extract", "chunk", "embed"])
def test_unknown_run_rejects_before_processing(processing, operation):
    processing["run"].return_value = None
    response = _request(operation)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
    _assert_no_processing(processing)


@pytest.mark.parametrize("operation", ["ingest", "extract", "chunk", "embed"])
def test_same_institution_processing_still_works(processing, operation):
    effects = processing["effects"]
    processing["run"].return_value["status"] = "queued" if operation == "extract" else "ready"
    effects["download_file"].return_value = b"test content"
    effects["extract_text"].return_value = "test content"
    effects["get_extracted_text"].return_value = "test content"
    effects["chunk_text"].return_value = [{"content_text": "test content"}]
    effects["embed_processing_run"].return_value = 1

    response = _request(operation)

    assert response.status_code == (201 if operation == "ingest" else 200)
    if operation == "ingest":
        effects["ingest_document"].assert_awaited_once()
    elif operation == "extract":
        effects["download_file"].assert_called_once()
        effects["store_extracted_text"].assert_called_once()
    elif operation == "chunk":
        effects["get_extracted_text"].assert_called_once()
        effects["delete_chunks_for_run"].assert_called_once()
        effects["insert_chunks"].assert_called_once()
    else:
        effects["embed_processing_run"].assert_called_once_with(RUN_ID)
