"""Conversation history regressions: ordering."""

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
                'knowledge_policy': {'institution_id': FAKE_USER_A['institution_id'], 'sources': {}, 'versions': {}},
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
    mock_client.rpc.return_value.execute.return_value.data = True
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
