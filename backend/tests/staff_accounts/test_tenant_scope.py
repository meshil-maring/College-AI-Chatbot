from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    UUID,
    _active_institution_authorization,
    _patch_staff_auth,
    client,
    patch,
)


def test_staff_own_institution_filter_is_accepted():
    """An own-institution query filter is accepted (Phase 6.4 contract)."""
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=[],
        ) as list_mock,
    ):
        response = client.get(
            "/api/v1/admin/students/pending",
            params={"institution_id": INSTITUTION_A},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)
