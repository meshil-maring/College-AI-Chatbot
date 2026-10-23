from .chat_helpers import (
    _gos_true_client,
    _institution_db,
    _login,
    _sign_in_account,
)
from .support import (
    INST_A1,
    MagicMock,
    STUDENT_LOGIN_URL,
    SafeAuthFailure,
    USER_STUDENT_A1,
    UUID,
    _active_institution_authorization,
    client,
    patch,
    pytest,
)


class TestAuthenticationSecurity:
    def test_valid_credentials_work(self):
        resp = _login(_sign_in_account())
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"] == "mock-access-token"

    def test_invalid_credentials_fail(self):
        resp = _login(_sign_in_account(), auth=_gos_true_client(success=False))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_missing_public_user_row_denied(self):
        resp = _login(None)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_user_status_denied(self):
        resp = _login(_sign_in_account(status="inactive"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_pending_student_cannot_bypass_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1,
                approval_status="pending",
                student_is_active=True,
            ),
            db=_institution_db(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_rejected_student_cannot_bypass_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1,
                approval_status="rejected",
                student_is_active=True,
            ),
            db=_institution_db(),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_institution_blocks_sign_in(self):
        """An approved student of a suspended institution cannot sign in."""
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1,
                approval_status="approved",
                student_is_active=True,
            ),
            db=_institution_db(is_active=False),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_approved_student_of_active_institution_can_sign_in(self):
        resp = _login(
            _sign_in_account(
                institution_id=INST_A1,
                approval_status="approved",
                student_is_active=True,
            ),
            db=_institution_db(is_active=True),
        )
        assert resp.status_code == 200, resp.text

    def _student_login(self, payload, result=None, error=None):
        if result is not None:
            result.setdefault("refresh_token", "student-refresh-token")
            result.setdefault("expires_in", 3600)
        with (
            patch(
                "app.api.auth.student_auth.authenticate_student",
                side_effect=error if error else None,
                return_value=None if error else result,
            ) as svc,
            patch("app.api.auth.student_auth.record_auth_security_event"),
        ):
            resp = client.post(STUDENT_LOGIN_URL, json=payload)
        return resp, svc

    def test_student_email_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {"identifier": "student@college.edu", "password": "secret123"},
            result=result,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"] == "student-token"
        assert svc.call_args.args[0] == "student@college.edu"

    def test_register_number_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {
                "identifier": "REG-1001",
                "password": "secret123",
                "institution_code": "IMPHAL",
            },
            result=result,
        )
        assert resp.status_code == 200, resp.text
        assert svc.call_args.args[0] == "REG-1001"
        assert svc.call_args.args[2] == "IMPHAL"

    def test_university_roll_number_login_works(self):
        result = {
            "access_token": "student-token",
            "user": {"id": USER_STUDENT_A1, "email": "student@college.edu"},
        }
        resp, svc = self._student_login(
            {
                "identifier": "ROLL-2024-77",
                "password": "secret123",
                "institution_code": "IMPHAL",
            },
            result=result,
        )
        assert resp.status_code == 200, resp.text
        assert svc.call_args.args[0] == "ROLL-2024-77"

    def test_academic_identifier_without_institution_code_rejected(self):
        resp, svc = self._student_login(
            {"identifier": "REG-1001", "password": "secret123"}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
        svc.assert_not_called()

    def test_identity_resolution_requires_institution_code(self):
        from app.services.auth.student_auth import _resolve_identity

        db = MagicMock()
        assert _resolve_identity(db, "REG-1001", None) is None
        assert _resolve_identity(db, "ROLL-2024-77", None) is None

    def test_admin_credentials_cannot_produce_student_session(self):
        resp, _ = self._student_login(
            {"identifier": "admin@college.edu", "password": "secret123"},
            error=SafeAuthFailure(),
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_institution_blocks_student_login(self):
        """The Phase 6.5 institution gate is enforced inside the service."""
        from app.services.auth.student_auth import authenticate_student

        db = _institution_db(is_active=False)
        with (
            patch("app.services.auth.student_auth.get_admin_client", return_value=db),
            patch(
                "app.services.auth.student_auth._resolve_identity",
                return_value=(
                    "student@college.edu",
                    UUID(INST_A1),
                    {
                        "email": "student@college.edu",
                        "approval_status": "approved",
                        "is_active": True,
                        "institution_id": INST_A1,
                    },
                ),
            ),
        ):
            with pytest.raises(SafeAuthFailure):
                authenticate_student("student@college.edu", "secret123", "IMPHAL")
