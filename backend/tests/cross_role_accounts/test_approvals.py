from .support import (
    ANY,
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    MagicMock,
    PENDING_STUDENT_ROW,
    STUDENT_A,
    STUDENT_B,
    UUID,
    _active_institution_authorization,
    _assert_forbidden,
    _assert_tenant_mismatch,
    _auth,
    client,
    patch,
)


def test_approval_queue_is_allowed_for_staff_and_admin_only():
    """staff + admin may list/approve/reject; student + faculty get 403."""
    with (
        _auth("staff"),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=[PENDING_STUDENT_ROW],
        ) as list_mock,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)

    with (
        _auth("admin"),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ),
    ):
        assert (
            client.get(
                "/api/v1/admin/students/pending", headers=AUTH_HEADERS
            ).status_code
            == 200
        )

    for role in ("student", "faculty"):
        _assert_forbidden(role, "GET", "/api/v1/admin/students/pending")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/approve")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/reject")


def test_denied_approval_attempts_never_reach_the_handler_or_write():
    """403 happens in the dependency: no approval service call, no write."""
    for role in ("student", "faculty"):
        with (
            _auth(role),
            patch("app.services.admin.admin_academics.approve_student") as approve_mock,
            patch("app.services.admin.admin_academics.reject_student") as reject_mock,
            patch("app.api.admin.common.record_admin_action") as audit_mock,
            patch("app.api.admin.common.get_admin_client") as client_mock,
        ):
            approve = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/approve", headers=AUTH_HEADERS
            )
            reject = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/reject", headers=AUTH_HEADERS
            )
        assert approve.status_code == 403, role
        assert reject.status_code == 403, role
        approve_mock.assert_not_called()
        reject_mock.assert_not_called()
        audit_mock.assert_not_called()
        client_mock.assert_not_called()


def test_staff_and_admin_approve_within_their_own_tenant():
    for role in ("staff", "admin"):
        with (
            _auth(role),
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
        assert response.status_code == 200, role
        assert response.json()["approval_status"] == "approved"
        approve_mock.assert_called_once_with(
            UUID(STUDENT_A), UUID(INSTITUTION_A), actor=ANY
        )
        assert approve_mock.call_args.kwargs["actor"]["roles"] == [role]
        # Approval audit is committed atomically by the provisioning command.
        audit_mock.assert_not_called()


def test_stale_approval_decision_produces_the_documented_409():
    """A rejected registration cannot be decided again and writes nothing."""
    already_decided = dict(PENDING_STUDENT_ROW, approval_status="rejected")
    for role in ("staff", "admin"):
        for operation in ("approve", "reject"):
            with (
                _auth(role),
                patch(
                    "app.services.admin.admin_academics.get_admin_client",
                    return_value=MagicMock(),
                ),
                patch(
                    "app.services.admin.admin_academics.academics_repo.get_student_for_approval",
                    return_value=already_decided,
                ),
                patch(
                    "app.services.admin.admin_academics.academics_repo.set_student_approval_status"
                ) as write_mock,
                patch("app.api.admin.common.record_admin_action") as audit_mock,
            ):
                response = client.post(
                    f"/api/v1/admin/students/{STUDENT_A}/{operation}",
                    headers=AUTH_HEADERS,
                )
            assert response.status_code == 409, f"{role} {operation}"
            assert response.json()["error"]["code"] == "STUDENT_NOT_PENDING"
            # The rejected/approved record is never mutated again.
            write_mock.assert_not_called()
            audit_mock.assert_not_called()


def test_platform_level_staff_and_faculty_hold_no_approval_authority():
    """Tenantless privileged users fail safely (Phase 6.4 OPTION A)."""
    for role in ("tenantless_staff", "tenantless_faculty"):
        _assert_forbidden(role, "GET", "/api/v1/admin/students/pending")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/approve")
        _assert_forbidden(role, "POST", f"/api/v1/admin/students/{STUDENT_A}/reject")


def test_staff_a_cannot_approve_or_reject_staff_bs_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    for operation in ("approve", "reject"):
        with (
            _auth("staff"),
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
            patch("app.api.admin.common.record_admin_action") as audit_mock,
        ):
            response = client.post(
                f"/api/v1/admin/students/{STUDENT_B}/{operation}", headers=AUTH_HEADERS
            )
        assert response.status_code == 403, operation
        assert response.json()["error"]["code"] == "TENANT_MISMATCH"
        # The foreign record is never mutated and no audit entry is written.
        write_mock.assert_not_called()
        audit_mock.assert_not_called()


def test_staff_a_cannot_list_staff_bs_pending_queue_via_parameters():
    _assert_tenant_mismatch(
        "staff",
        "GET",
        "/api/v1/admin/students/pending",
        params={"institution_id": INSTITUTION_B},
    )
