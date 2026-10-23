from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    UUID,
    _patch_admin_auth,
    build_dashboard,
    client,
    patch,
)


def test_admin_dashboard_scoped_to_own_tenant():
    with (
        _patch_admin_auth(),
        patch(
            "app.services.admin.admin_dashboard.get_dashboard_summary",
            return_value=build_dashboard(),
        ) as dash_mock,
    ):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 200
    # Phase 7.21: the tenant comes only from the server authorization context.
    dash_mock.assert_called_once_with(institution_id=UUID(INSTITUTION_A))
