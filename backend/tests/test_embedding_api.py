"""Tests for the Phase 3.6F embedding API route."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

RUN_ID = "a0000000-0000-0000-0000-000000000003"

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}
FAKE_USER = {
    "user_id": "30000000-0000-0000-0000-000000000101",
    "auth_user_id": FAKE_CLAIMS["sub"],
    "email": FAKE_CLAIMS["email"],
    "roles": ["staff"],
}


def _auth_headers():
    return {"Authorization": "Bearer valid.token.here"}


def _patch_auth():
    return (
        patch("app.core.security.verify_jwt", return_value=FAKE_CLAIMS),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=FAKE_USER)),
    )


def test_embed_success_delegates_and_returns_embedded_status():
    verify, user = _patch_auth()
    embed_mock = MagicMock(return_value=3)
    with verify, user, patch("app.api.ingestion.embed_processing_run", embed_mock):
        response = client.post(
            f"/api/v1/documents/{RUN_ID}/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json() == {
        "processing_run_id": RUN_ID,
        "status": "embedded",
        "embeddings_created": 3,
    }
    embed_mock.assert_called_once_with(RUN_ID)


def test_embed_already_embedded_response_is_terminal_without_route_regeneration():
    verify, user = _patch_auth()
    embed_mock = MagicMock(return_value=0)
    with (
        verify,
        user,
        patch("app.api.ingestion.embed_processing_run", embed_mock),
        patch("app.api.ingestion.update_run_status") as update_status,
        patch("openai.OpenAI") as openai_client,
    ):
        response = client.post(
            f"/api/v1/documents/{RUN_ID}/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "embedded"
    update_status.assert_not_called()
    openai_client.assert_not_called()


def test_embed_invalid_processing_run_id_uses_fastapi_validation():
    verify, user = _patch_auth()
    with verify, user, patch("app.api.ingestion.embed_processing_run") as embed_mock:
        response = client.post(
            "/api/v1/documents/not-a-uuid/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 422
    embed_mock.assert_not_called()


def test_embed_app_error_uses_application_error_handler():
    verify, user = _patch_auth()
    error = AppError("Run is not available for embedding", status_code=409, code="RUN_NOT_EMBEDDABLE")
    with verify, user, patch("app.api.ingestion.embed_processing_run", side_effect=error):
        response = client.post(
            f"/api/v1/documents/{RUN_ID}/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "RUN_NOT_EMBEDDABLE",
            "message": "Run is not available for embedding",
        }
    }


def test_embed_unexpected_service_failure_uses_existing_500_convention():
    verify, user = _patch_auth()
    with verify, user, patch(
        "app.api.ingestion.embed_processing_run",
        side_effect=RuntimeError("unexpected failure"),
    ):
        response = client.post(
            f"/api/v1/documents/{RUN_ID}/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_embed_requires_the_existing_ingestion_roles():
    response = client.post(f"/api/v1/documents/{RUN_ID}/embed")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_embed_route_does_not_update_processing_run_status():
    verify, user = _patch_auth()
    embed_mock = MagicMock(return_value=1)
    with (
        verify,
        user,
        patch("app.api.ingestion.embed_processing_run", embed_mock),
        patch("app.api.ingestion.get_admin_client") as get_admin_client,
        patch("app.api.ingestion.update_run_status") as update_status,
    ):
        response = client.post(
            f"/api/v1/documents/{RUN_ID}/embed",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    embed_mock.assert_called_once_with(RUN_ID)
    get_admin_client.assert_not_called()
    update_status.assert_not_called()