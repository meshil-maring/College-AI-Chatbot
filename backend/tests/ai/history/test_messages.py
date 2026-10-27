"""Conversation history regressions: messages."""

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
