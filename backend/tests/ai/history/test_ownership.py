"""Conversation history regressions: ownership."""

from __future__ import annotations

from .support import (
    FAKE_CLAIMS_A,
    FAKE_USER_A,
    FAKE_USER_B,
    MagicMock,
    _auth_header,
    _patch_admin,
    _patch_auth,
    client,
)


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
