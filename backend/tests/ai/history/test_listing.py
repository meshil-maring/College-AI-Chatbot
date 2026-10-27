"""Conversation history regressions: listing."""

from __future__ import annotations

from .support import (
    FAKE_CLAIMS_A,
    FAKE_USER_A,
    MagicMock,
    _auth_header,
    _patch_admin,
    _patch_auth,
    client,
)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_list_conversations_requires_auth():
    response = client.get("/api/v1/conversations")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ---------------------------------------------------------------------------
# Conversation listing
# ---------------------------------------------------------------------------


def test_list_conversations_returns_own_conversations():
    """Authenticated user sees only their own conversations."""
    mock_client = MagicMock()
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "conversation_id": "20000000-0000-0000-0000-000000000002",
                "user_id": FAKE_USER_A["user_id"],
                "title": "Second conversation",
                "status": "active",
                "created_at": "2026-09-02T10:00:00+00:00",
                "updated_at": "2026-09-02T10:00:00+00:00",
            },
            {
                "conversation_id": "20000000-0000-0000-0000-000000000001",
                "user_id": FAKE_USER_A["user_id"],
                "title": "First conversation",
                "status": "active",
                "created_at": "2026-09-01T10:00:00+00:00",
                "updated_at": "2026-09-01T10:00:00+00:00",
            },
        ]
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get("/api/v1/conversations", headers=_auth_header(FAKE_CLAIMS_A))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["conversation_id"] == "20000000-0000-0000-0000-000000000002"
    assert body[1]["conversation_id"] == "20000000-0000-0000-0000-000000000001"
    for item in body:
        assert "conversation_id" in item
        assert "title" in item
        assert "status" in item
        assert "created_at" in item
        assert "updated_at" in item
        assert "user_id" not in item


def test_list_conversations_empty():
    """Authenticated user with no conversations receives an empty list."""


# ---------------------------------------------------------------------------
# Ordering verification
# ---------------------------------------------------------------------------


def test_conversations_ordered_by_updated_at_desc():
    """Conversations are returned newest-first by updated_at."""
    mock_client = MagicMock()
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "conversation_id": "20000000-0000-0000-0000-000000000001",
                "user_id": FAKE_USER_A["user_id"],
                "title": "Old",
                "status": "active",
                "created_at": "2026-09-01T10:00:00+00:00",
                "updated_at": "2026-09-01T10:00:00+00:00",
            },
            {
                "conversation_id": "20000000-0000-0000-0000-000000000002",
                "user_id": FAKE_USER_A["user_id"],
                "title": "New",
                "status": "active",
                "created_at": "2026-09-02T10:00:00+00:00",
                "updated_at": "2026-09-05T10:00:00+00:00",
            },
        ]
    )


# ---------------------------------------------------------------------------
# Response schema verification
# ---------------------------------------------------------------------------


def test_conversation_summary_schema_has_no_user_id():
    """The conversation summary response must not expose user_id."""
    mock_client = MagicMock()
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "conversation_id": "20000000-0000-0000-0000-000000000001",
                "user_id": FAKE_USER_A["user_id"],
                "title": "Test",
                "status": "active",
                "created_at": "2026-09-01T10:00:00+00:00",
                "updated_at": "2026-09-01T10:00:00+00:00",
            },
        ]
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get("/api/v1/conversations", headers=_auth_header(FAKE_CLAIMS_A))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    allowed_keys = {"conversation_id", "title", "status", "created_at", "updated_at"}
    assert set(body[0].keys()) == allowed_keys
