from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    MagicMock,
    PENDING_STUDENT_ROW,
    STUDENT_A,
    STUDENT_APPROVAL_COLUMNS,
    STUDENT_B,
    TENANT_LESS_STAFF_USER,
    UUID,
    _active_institution_authorization,
    _patch_staff_auth,
    client,
    patch,
)


def test_staff_lists_pending_students_for_own_tenant():
    """Tenant-bound staff always receive their OWN institution's queue; the
    tenant is resolved server-side and no institution_id is needed."""
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=[PENDING_STUDENT_ROW],
        ) as list_mock,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)


def test_staff_foreign_institution_filter_rejected_with_tenant_mismatch():
    """A foreign ?institution_id= can never widen the staff queue scope."""
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
        ) as list_mock,
    ):
        response = client.get(
            "/api/v1/admin/students/pending",
            params={"institution_id": INSTITUTION_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    list_mock.assert_not_called()


def test_staff_approves_pending_student_within_own_tenant():
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.approve_student",
            return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
        ) as approve_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"
    assert approve_mock.call_count == 1
    assert approve_mock.call_args.args == (UUID(STUDENT_A), UUID(INSTITUTION_A))
    assert approve_mock.call_args.kwargs["actor"]["auth_user_id"]
    audit_mock.assert_not_called()


def test_staff_rejects_pending_student_within_own_tenant():
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.reject_student",
            return_value=dict(PENDING_STUDENT_ROW, approval_status="rejected"),
        ) as reject_mock,
        patch("app.api.admin.common.record_admin_action"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/reject", headers=AUTH_HEADERS
        )
    assert response.status_code == 200
    assert response.json()["approval_status"] == "rejected"
    reject_mock.assert_called_once_with(UUID(STUDENT_A), UUID(INSTITUTION_A))


def test_staff_cannot_approve_cross_tenant_student():
    """Staff A (Institution A) cannot approve Institution B's student. The
    service enforces tenant BEFORE any state change; no write happens."""
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.admin.admin_academics.academics_repo.get_student_for_approval",
            return_value=foreign_student,
        ),
        patch(
            "app.services.admin.admin_academics.academics_repo.set_student_approval_status"
        ) as write_mock,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()


def test_staff_cannot_reject_cross_tenant_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.admin.admin_academics.academics_repo.get_student_for_approval",
            return_value=foreign_student,
        ),
        patch(
            "app.services.admin.admin_academics.academics_repo.set_student_approval_status"
        ) as write_mock,
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/reject", headers=AUTH_HEADERS
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    write_mock.assert_not_called()


def test_platform_level_staff_denied_approval_authority():
    """A tenant-less staff account never gains approval authority (Phase 6.4
    OPTION A: the privilege-escalation surface stays closed)."""
    for method, path in (
        ("GET", "/api/v1/admin/students/pending"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A}/approve"),
        ("POST", f"/api/v1/admin/students/{STUDENT_A}/reject"),
    ):
        with _patch_staff_auth(user=TENANT_LESS_STAFF_USER):
            response = client.request(method, path, headers=AUTH_HEADERS)
        assert response.status_code == 403, f"{method} {path}: {response.status_code}"
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staff_cannot_widen_approval_scope_with_identity_parameters():
    """student_id/institution_id supplied by the client are never an
    authorization mechanism: approval scope comes from the JWT context."""
    with (
        _patch_staff_auth(),
        patch(
            "app.services.admin.admin_academics.approve_student",
            return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
        ) as approve_mock,
        patch("app.api.admin.common.record_admin_action"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve",
            params={"institution_id": INSTITUTION_B, "staff_id": "x"},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200  # body accepts NO fields; params are inert
    assert approve_mock.call_count == 1
    assert approve_mock.call_args.args == (UUID(STUDENT_B), UUID(INSTITUTION_A))
    assert approve_mock.call_args.kwargs["actor"]["auth_user_id"]


def test_approval_queue_projection_never_contains_secret_material():
    """The only student payload a staff client receives is the minimal
    Phase 6.4 approval projection — no credentials, no token material."""
    forbidden = ("password", "token", "secret", "encrypted_password")
    lowered = STUDENT_APPROVAL_COLUMNS.lower()
    for needle in forbidden:
        assert needle not in lowered, needle
    # The projection stays minimal and approval-oriented.
    assert "approval_status" in lowered
    assert "student_number" in lowered
