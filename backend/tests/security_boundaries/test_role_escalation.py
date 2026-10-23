from .support import (
    AppError,
    INST_A1,
    INST_B1,
    JR_A,
    ORG_A,
    ORG_B,
    STUDENT_ID_A1,
    USER_INST_A1,
    USER_ORG_A,
    USER_STUDENT_A1,
    _active_institution_authorization,
    _as,
    _clear,
    _resolve,
    _role_row,
    _user,
    asyncio,
    authz,
    client,
    pytest,
    require_roles,
)


class TestRoleEscalation:
    def test_student_cannot_become_admin(self):
        student = _user(INST_A1, roles=("student",), user_id=USER_STUDENT_A1)
        with pytest.raises(AppError) as exc:
            asyncio.run(require_roles("admin")(current_user=student))
        assert exc.value.status_code == 403
        assert exc.value.code == "FORBIDDEN"

    def test_institution_admin_cannot_escalate_to_organization_scope(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(
                _user(user_id=USER_INST_A1), ctx, ORG_A
            )
        assert exc.value.code == "FORBIDDEN"

    def test_institution_a_admin_cannot_reach_institution_b(self):
        ctx = _resolve([_role_row(authz.INSTITUTION, INST_A1, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_institution(
                _user(user_id=USER_INST_A1), ctx, INST_B1
            )
        assert exc.value.code == "TENANT_MISMATCH"

    def test_org_a_admin_cannot_reach_org_b(self):
        ctx = _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
        with pytest.raises(AppError) as exc:
            authz.assert_can_manage_organization(_user(user_id=USER_ORG_A), ctx, ORG_B)
        assert exc.value.code == "ORGANIZATION_MISMATCH"

    def test_scope_columns_cannot_be_widened_by_client(self):
        """scope_type / scope_id sent in a decision body are rejected."""
        _as(_user(user_id=USER_ORG_A))
        try:
            resp = client.post(
                f"/api/v1/institutions/join-requests/{JR_A}/decision",
                json={
                    "decision": "approve",
                    "role": "admin",
                    "scope_type": "platform",
                    "scope_id": ORG_B,
                    "organization_id": ORG_B,
                },
            )
        finally:
            _clear()
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_login_cannot_supply_role_or_scope(self):
        base = {"email": "u@example.com", "password": "secret123"}
        for extra in (
            {"role": "admin"},
            {"roles": ["admin"]},
            {"scope_type": "platform"},
            {"scope_id": ORG_A},
            {"organization_id": ORG_A},
            {"institution_id": INST_A1},
        ):
            resp = client.post("/api/v1/auth/login", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_student_login_cannot_supply_identity_fields(self):
        base = {"identifier": "student@college.edu", "password": "pw123456"}
        for extra in (
            {"role": "admin"},
            {"user_id": USER_STUDENT_A1},
            {"student_id": STUDENT_ID_A1},
            {"institution_id": INST_B1},
            {"approval_status": "approved"},
        ):
            resp = client.post("/api/v1/auth/student/login", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_public_registration_cannot_supply_role_scope_or_identity(self):
        base = {
            "institution_code": "IMPHAL",
            "email": "new@college.edu",
            "password": "secret123",
            "first_name": "New",
            "last_name": "Student",
            "registration_type": "student",
            "register_number": "REG1",
        }
        for extra in (
            {"role": "admin"},
            {"scope_type": "platform"},
            {"user_id": USER_STUDENT_A1},
            {"student_id": STUDENT_ID_A1},
            {"institution_id": INST_B1},
            {"approval_status": "approved"},
        ):
            resp = client.post("/api/v1/users/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_organization_registration_cannot_supply_role_or_status(self):
        base = {
            "name": "New Org",
            "organization_code": "NEWORG",
            "official_email": "info@neworg.example.com",
            "contact_information": "contact@neworg.example.com",
            "admin_email": "admin@neworg.example.com",
            "admin_password": "secret123",
            "admin_first_name": "Org",
            "admin_last_name": "Admin",
        }
        for extra in (
            {"role": "admin"},
            {"scope_type": "platform"},
            {"status": "active"},
            {"join_code": "HACKED"},
        ):
            resp = client.post("/api/v1/organizations/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)

    def test_institution_registration_cannot_supply_org_or_role(self):
        base = {
            "name": "New Campus",
            "institution_code": "NEWCAMP",
            "organization_code": "ACME",
            "official_email": "info@newcamp.example.com",
            "admin_email": "admin@newcamp.example.com",
            "admin_password": "secret123",
            "admin_first_name": "Inst",
            "admin_last_name": "Admin",
        }
        for extra in (
            {"organization_id": ORG_B},
            {"role": "admin"},
            {"status": "active"},
            {"is_active": True},
        ):
            resp = client.post("/api/v1/institutions/register", json={**base, **extra})
            assert resp.status_code == 422, (extra, resp.text)
