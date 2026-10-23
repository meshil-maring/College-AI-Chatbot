from .database import (
    _FakeClient,
)
from .state import (
    _inst_row,
)
from .support import (
    AppError,
    INST_A1,
    ORG_A,
    USER_STUDENT_A1,
    _active_institution_authorization,
    _deep_values,
    patch,
    pytest,
    tenancy_repo,
)


class TestRegistrationSecurity:
    def test_users_cannot_register_into_non_active_institution(self):
        from app.schemas.auth.users import UserRegistrationRequest
        from app.services.auth import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="PENDINGC",
            email="new@college.edu",
            password="secret123",
            first_name="New",
            last_name="Student",
            register_number="REG-1",
        )
        fake = _FakeClient({})
        for status in ("pending", "rejected", "suspended"):
            with (
                patch.object(svc, "get_admin_client", return_value=fake),
                patch.object(
                    tenancy_repo,
                    "get_institution_by_code",
                    return_value=_inst_row(INST_A1, ORG_A, status),
                ),
            ):
                with pytest.raises(AppError) as exc:
                    svc.register_user(payload)
            assert exc.value.status_code == 403
            assert exc.value.code == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"

    def test_duplicate_email_registration_rejected(self):
        from app.schemas.auth.users import UserRegistrationRequest
        from app.services.auth import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="dupe@college.edu",
            password="secret123",
            first_name="Dupe",
            last_name="Student",
            register_number="REG-2",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(
                svc.student_svc,
                "_find_user_by_email",
                return_value={"user_id": USER_STUDENT_A1},
            ),
            patch.object(
                svc.academics_repo, "get_student_by_user_id", return_value=None
            ),
        ):
            with pytest.raises(AppError) as exc:
                svc.register_user(payload)
        assert exc.value.status_code == 409
        assert exc.value.code == "EMAIL_ALREADY_REGISTERED"

    def test_duplicate_academic_identifier_rejected(self):
        """The existing institution-scoped duplicate guard is enforced."""
        from app.schemas.auth.users import UserRegistrationRequest
        from app.services.auth import user_registration as svc

        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="new@college.edu",
            password="secret123",
            first_name="New",
            last_name="Student",
            register_number="REG-DUP",
        )
        fake = _FakeClient({})
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(svc.student_svc, "_find_user_by_email", return_value=None),
            patch.object(
                svc.student_svc,
                "_assert_no_duplicate_identities",
                side_effect=AppError(
                    "Register number already registered",
                    status_code=409,
                    code="REGISTER_NUMBER_ALREADY_REGISTERED",
                ),
            ) as guard,
        ):
            with pytest.raises(AppError) as exc:
                svc.register_user(payload)
        assert exc.value.code == "REGISTER_NUMBER_ALREADY_REGISTERED"
        guard.assert_called_once()

    def test_registration_password_never_reaches_application_tables(self):
        """The password goes ONLY to Supabase Auth (GoTrue)."""
        from app.schemas.auth.users import UserRegistrationRequest
        from app.services.auth import user_registration as svc

        secret = "Sup3rSecret!Pass"
        payload = UserRegistrationRequest(
            registration_type="student",
            institution_code="IMPHAL",
            email="new@college.edu",
            password=secret,
            first_name="New",
            last_name="Student",
            register_number="REG-PW",
        )
        fake = _FakeClient({})
        auth_calls = []
        with (
            patch.object(svc, "get_admin_client", return_value=fake),
            patch.object(
                tenancy_repo,
                "get_institution_by_code",
                return_value=_inst_row(INST_A1, ORG_A, "active"),
            ),
            patch.object(svc.student_svc, "_find_user_by_email", return_value=None),
            patch.object(
                svc.student_svc, "_assert_no_duplicate_identities", return_value=None
            ),
            patch.object(
                svc.student_svc,
                "_create_auth_account",
                side_effect=lambda email, pw: auth_calls.append(pw) or "auth-id",
            ),
            patch.object(
                svc.student_svc, "_create_public_user", return_value=USER_STUDENT_A1
            ),
        ):
            response = svc.register_user(payload)

        # The password was handed to GoTrue exactly once...
        assert auth_calls == [secret]
        # ...and never written into any application table row.
        app_tables = {k: v for k, v in fake.state.items() if k not in {"accesses"}}
        for value in _deep_values(app_tables):
            assert secret not in value
        # Neither is it exposed on the response.
        assert secret not in response.model_dump_json()
