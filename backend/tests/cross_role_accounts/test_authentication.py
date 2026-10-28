from .support import (
    ALL_FOUR_ROLES,
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    SUPPORTED_ROLES,
    _active_institution_authorization,
    _auth,
    client,
    resolve_primary_role,
)


def test_role_resolution_matrix_is_unchanged():
    """Each role resolves to itself; precedence stays admin > staff > faculty > student."""
    assert resolve_primary_role(["student"]) == "student"
    assert resolve_primary_role(["faculty"]) == "faculty"
    assert resolve_primary_role(["staff"]) == "staff"
    assert resolve_primary_role(["admin"]) == "admin"
    # Precedence is untouched by this phase.
    assert resolve_primary_role(["student", "faculty"]) == "faculty"
    assert resolve_primary_role(["student", "staff"]) == "staff"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["staff", "admin"]) == "admin"
    assert resolve_primary_role(list(SUPPORTED_ROLES)) == "super_admin"
    # Unsupported/null roles never resolve to a privileged role.
    assert resolve_primary_role(["unknown-role"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_resolves_each_role_with_its_own_tenant():
    for role in ALL_FOUR_ROLES:
        with _auth(role):
            response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
        assert response.status_code == 200, role
        body = response.json()
        assert body["authenticated"] is True
        assert body["role"] == role
        assert body["institution_id"] == INSTITUTION_A
        # No token/secret material is ever part of the identity payload.
        expected_fields = {
            "authenticated",
            "user_id",
            "auth_user_id",
            "email",
            "role",
            "institution_id",
            "effective_permissions",
        }
        if role == "admin":
            expected_fields.add("institution_code")
        assert set(body) == expected_fields


def test_auth_me_never_derives_the_role_from_client_parameters():
    """URL/localStorage/body role values cannot influence the resolved role."""
    for role in ALL_FOUR_ROLES:
        with _auth(role):
            response = client.get(
                "/api/v1/auth/me",
                headers=AUTH_HEADERS,
                params={
                    "role": "admin",
                    "institution_id": INSTITUTION_B,
                    "user_id": "client-supplied",
                    "tenant_id": INSTITUTION_B,
                },
            )
        assert response.status_code == 200, role
        body = response.json()
        assert body["role"] == role, role
        assert body["institution_id"] == INSTITUTION_A, role


def test_unsupported_role_resolves_to_no_privileged_context():
    with _auth("unsupported"):
        response = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["role"] is None
    # Phase 7.20: with no supported role there is no ``user_roles`` grant, so no
    # institution scope is projected (an unrelated tenant is never inherited).
    assert response.json()["institution_id"] is None
