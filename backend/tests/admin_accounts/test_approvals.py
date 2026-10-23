from .support import (
    AUTH_HEADERS,
    INSTITUTION_A,
    INSTITUTION_B,
    MagicMock,
    PENDING_STUDENT_ROW,
    STUDENT_A,
    STUDENT_B,
    UUID,
    _patch_admin_auth,
    _patch_role_auth,
    client,
    patch,
)


def test_staff_approval_exception_remains_intact():
    with (
        _patch_role_auth("staff"),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=[PENDING_STUDENT_ROW],
        ),
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]


def test_admin_lists_pending_students_scoped_to_own_tenant():
    with (
        _patch_admin_auth(),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=[PENDING_STUDENT_ROW],
        ) as list_mock,
    ):
        response = client.get("/api/v1/admin/students/pending", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == [PENDING_STUDENT_ROW]
    list_mock.assert_called_once_with(UUID(INSTITUTION_A), limit=100, offset=0)


def test_admin_foreign_institution_filter_rejected():
    """A foreign ?institution_id= can never widen the queue scope."""
    with (
        _patch_admin_auth(),
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


def test_admin_approves_pending_student_within_own_tenant():
    db = MagicMock()
    with (
        _patch_admin_auth(),
        patch(
            "app.services.admin.admin_academics.approve_student",
            return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
        ) as approve_mock,
        patch("app.api.admin.common.record_admin_action") as audit_mock,
        patch("app.api.admin.common.get_admin_client", return_value=db),
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


def test_admin_cannot_approve_cross_tenant_student():
    """Institution A's admin cannot approve Institution B's student. Tenant
    is enforced BEFORE any state change; no write happens."""
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with (
        _patch_admin_auth(),
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


def test_admin_cannot_reject_cross_tenant_student():
    foreign_student = dict(PENDING_STUDENT_ROW, institution_id=INSTITUTION_B)
    with (
        _patch_admin_auth(),
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


def test_admin_approval_identity_params_are_inert():
    """Approve bodies accept NO fields: client identity params never change
    the decision target or tenant (both come from path + JWT context)."""
    with (
        _patch_admin_auth(),
        patch(
            "app.services.admin.admin_academics.approve_student",
            return_value=dict(PENDING_STUDENT_ROW, approval_status="approved"),
        ) as approve_mock,
        patch("app.api.admin.common.record_admin_action"),
        patch("app.api.admin.common.get_admin_client", return_value=MagicMock()),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_A}/approve",
            params={"institution_id": INSTITUTION_B, "student_id": STUDENT_B},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 200
    assert approve_mock.call_args.args == (UUID(STUDENT_A), UUID(INSTITUTION_A))
    assert approve_mock.call_args.kwargs["actor"]["auth_user_id"]
