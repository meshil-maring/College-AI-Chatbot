from .support import (
    AUTH_HEADERS,
    _active_institution_authorization,
    _patch_staff_auth,
    client,
    patch,
)


def test_staff_can_list_own_conversations():
    """Conversations authenticate with get_current_user (any role) and scope
    to the authenticated user_id server-side."""
    with (
        _patch_staff_auth(),
        patch(
            "app.api.ai.conversations.get_user_conversations",
            return_value=[],
        ) as conversations_mock,
    ):
        response = client.get("/api/v1/conversations", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == []
    conversations_mock.assert_called_once()
