"""Phase 5.6 - Tests for the conversation history API."""

from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FAKE_CLAIMS_A = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "user-a@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_CLAIMS_B = {
    "sub": "11111111-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "user-b@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_USER_A = {
    "user_id": "10000000-0000-0000-0000-000000000001",
    "auth_user_id": FAKE_CLAIMS_A["sub"],
    "email": FAKE_CLAIMS_A["email"],
    "roles": ["student"],
}

FAKE_USER_B = {
    "user_id": "10000000-0000-0000-0000-000000000002",
    "auth_user_id": FAKE_CLAIMS_B["sub"],
    "email": FAKE_CLAIMS_B["email"],
    "roles": ["student"],
}


def _auth_header(claims):
    return {"Authorization": "Bearer fake.token"}


def _patch_auth(user=FAKE_USER_A, claims=FAKE_CLAIMS_A):
    return (
        patch("app.core.security.verify_jwt", return_value=claims),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user)),
    )


def _patch_admin(client_mock):
    return patch("app.services.conversation_history.get_admin_client", return_value=client_mock)


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
# Message retrieval
# ---------------------------------------------------------------------------


def test_get_messages_returns_owned_messages():
    """Owner can retrieve messages for their conversation."""
    conversation_id = "20000000-0000-0000-0000-000000000001"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": conversation_id,
            "user_id": FAKE_USER_A["user_id"],
            "title": "Test conversation",
            "status": "active",
        }
    )
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "message_id": "30000000-0000-0000-0000-000000000001",
                "conversation_id": conversation_id,
                "message_sequence": 1,
                "message_type": "user",
                "content_text": "Hello",
                "created_at": "2026-09-01T10:00:00+00:00",
            },
            {
                "message_id": "30000000-0000-0000-0000-000000000002",
                "conversation_id": conversation_id,
                "message_sequence": 2,
                "message_type": "assistant",
                "content_text": "Hi there!",
                "created_at": "2026-09-01T10:00:05+00:00",
            },
        ]
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["message_sequence"] == 1
    assert body[0]["message_type"] == "user"
    assert body[0]["content_text"] == "Hello"
    assert body[1]["message_sequence"] == 2
    assert body[1]["message_type"] == "assistant"
    assert body[1]["content_text"] == "Hi there!"

# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


def test_cross_user_cannot_access_conversation_messages():
    """User A cannot retrieve User B's conversation messages."""
    conversation_id = "20000000-0000-0000-0000-000000000001"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": conversation_id,
            "user_id": FAKE_USER_B["user_id"],
            "title": "User B conversation",
            "status": "active",
        }
    )

    jwt_patch, db_patch = _patch_auth(user=FAKE_USER_A, claims=FAKE_CLAIMS_A)
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"


def test_cross_user_unknown_conversation_returns_404():
    """Requesting a non-existent conversation returns 404."""
    conversation_id = "20000000-0000-0000-0000-000000000099"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data=None
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"


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


def test_message_summary_schema_fields():
    """The message summary response exposes only the supported fields."""
    conversation_id = "20000000-0000-0000-0000-000000000001"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": conversation_id,
            "user_id": FAKE_USER_A["user_id"],
            "title": "Test",
            "status": "active",
        }
    )
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "message_id": "30000000-0000-0000-0000-000000000001",
                "conversation_id": conversation_id,
                "message_sequence": 1,
                "message_type": "user",
                "content_text": "Hello",
                "created_at": "2026-09-01T10:00:00+00:00",
            },
        ]
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    allowed_keys = {
        "message_id",
        "conversation_id",
        "message_sequence",
        "message_type",
        "content_text",
        "created_at",
    }
    assert set(body[0].keys()) == allowed_keys


def test_messages_ordered_by_sequence_asc():
    """Messages are returned in chronological order by message_sequence."""
    conversation_id = "20000000-0000-0000-0000-000000000001"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": conversation_id,
            "user_id": FAKE_USER_A["user_id"],
            "title": "Test",
            "status": "active",
        }
    )
    mock_client.table().select().eq().order().execute.return_value = MagicMock(
        data=[
            {
                "message_id": "30000000-0000-0000-0000-000000000001",
                "conversation_id": conversation_id,
                "message_sequence": 1,
                "message_type": "user",
                "content_text": "First",
                "created_at": "2026-09-01T10:00:00+00:00",
            },
            {
                "message_id": "30000000-0000-0000-0000-000000000002",
                "conversation_id": conversation_id,
                "message_sequence": 2,
                "message_type": "assistant",
                "content_text": "Second",
                "created_at": "2026-09-01T10:00:05+00:00",
            },
            {
                "message_id": "30000000-0000-0000-0000-000000000003",
                "conversation_id": conversation_id,
                "message_sequence": 3,
                "message_type": "user",
                "content_text": "Third",
                "created_at": "2026-09-01T10:00:10+00:00",
            },
        ]
    )

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 200
    body = response.json()
    assert [m["content_text"] for m in body] == ["First", "Second", "Third"]
    assert [m["message_sequence"] for m in body] == [1, 2, 3]
    assert body[1]["message_sequence"] == 2
    assert body[1]["message_type"] == "assistant"
    assert body[1]["content_text"] == "Second"


def test_get_messages_empty_conversation():
    """Conversation with no messages returns an empty list."""
    conversation_id = "20000000-0000-0000-0000-000000000001"
    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": conversation_id,
            "user_id": FAKE_USER_A["user_id"],
            "title": "Empty conversation",
            "status": "active",
        }
    )
    mock_client.table().select().eq().order().execute.return_value = MagicMock(data=[])

    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch, _patch_admin(mock_client):
        response = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_header(FAKE_CLAIMS_A),
        )

    assert response.status_code == 200
    assert response.json() == []