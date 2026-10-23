from .database import (
    _FakeClient,
)
from .state import (
    _org_row,
)
from .support import (
    AppError,
    INST_B1,
    ORG_B,
    ROLE_ID,
    USER_INST_A1,
    USER_ORG_A,
    UUID,
    _active_institution_authorization,
    client,
    patch,
    pytest,
    tenancy_repo,
)


class TestRegistrationSecurity:
    def test_registration_type_admin_is_unrepresentable(self):
        base = {
            "institution_code": "IMPHAL",
            "email": "admin-wannabe@college.edu",
            "password": "secret123",
            "first_name": "Wan",
            "last_name": "Nabe",
        }
        for role in ("admin", "institution_admin", "organization_admin"):
            resp = client.post(
                "/api/v1/users/register",
                json={**base, "registration_type": role},
            )
            assert resp.status_code == 422, (role, resp.text)
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_organization_registration_grants_only_server_chosen_admin_scope(self):
        from app.schemas.platform.tenancy import OrganizationRegistrationRequest
        from app.services.platform import tenancy as svc

        payload = OrganizationRegistrationRequest(
            name="New Org",
            organization_code="neworg",
            official_email="info@neworg.example.com",
            contact_information="contact",
            admin_email="admin@neworg.example.com",
            admin_password="secret123",
            admin_first_name="Org",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        calls = {}
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(tenancy_repo, "organization_code_exists", return_value=False),
            patch.object(tenancy_repo, "get_user_by_email", return_value=None),
            patch.object(svc, "_create_auth_account", return_value="auth-id"),
            patch.object(svc, "_create_public_user", return_value=USER_ORG_A),
            patch.object(
                tenancy_repo, "get_role_by_name", return_value={"role_id": ROLE_ID}
            ),
        ):

            def _assign(db, **kwargs):
                calls.update(kwargs)
                return {}

            with patch.object(
                tenancy_repo, "assign_user_role_scope", side_effect=_assign
            ):
                response = svc.register_organization(payload)

        assert calls["role_id"] == ROLE_ID
        assert calls["scope_type"] == "organization"
        assert calls["scope_id"] == calls["scope_organization_id"]
        assert response.status == "pending"

    def test_institution_registration_uses_server_resolved_organization(self):
        """A client cannot bypass organization ownership by supplying ids."""
        from app.schemas.platform.tenancy import InstitutionRegistrationRequest
        from app.services.platform import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        inserted = {}
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_organization_by_code",
                return_value=_org_row(ORG_B, "active"),
            ),
            patch.object(tenancy_repo, "institution_code_exists", return_value=False),
            patch.object(tenancy_repo, "get_user_by_email", return_value=None),
            patch.object(svc, "_create_auth_account", return_value="auth-id"),
            patch.object(svc, "_create_public_user", return_value=USER_INST_A1),
            patch.object(
                tenancy_repo, "get_role_by_name", return_value={"role_id": ROLE_ID}
            ),
            patch.object(tenancy_repo, "assign_user_role_scope", return_value={}),
            patch.object(tenancy_repo, "insert_join_request", return_value={}),
        ):

            def _insert(db, **kwargs):
                inserted.update(kwargs)
                return {
                    "institution_id": INST_B1,
                    "organization_id": kwargs["organization_id"],
                    "code": kwargs["code"],
                    "status": "pending",
                }

            with patch.object(tenancy_repo, "insert_institution", side_effect=_insert):
                response = svc.register_institution(payload)

        # The institution is bound to the SERVER-RESOLVED organization (B).
        assert inserted["organization_id"] == ORG_B
        assert response.organization_id == UUID(ORG_B)
        assert response.status == "pending"

    def test_institution_registration_rejects_non_active_organization(self):
        from app.schemas.platform.tenancy import InstitutionRegistrationRequest
        from app.services.platform import tenancy as svc

        payload = InstitutionRegistrationRequest(
            name="New Campus",
            institution_code="NEWCAMP",
            organization_code="BETA",
            official_email="info@newcamp.example.com",
            admin_email="admin@newcamp.example.com",
            admin_password="secret123",
            admin_first_name="Inst",
            admin_last_name="Admin",
        )
        fake = _FakeClient({})
        for status in ("pending", "rejected", "suspended"):
            with (
                patch.object(svc, "get_admin_client", return_value=fake),
                patch.object(
                    tenancy_repo,
                    "get_organization_by_code",
                    return_value=_org_row(ORG_B, status),
                ),
            ):
                with pytest.raises(AppError) as exc:
                    svc.register_institution(payload)
            assert exc.value.status_code == 403
            assert exc.value.code == "ORGANIZATION_NOT_ACCEPTING_REQUESTS"
