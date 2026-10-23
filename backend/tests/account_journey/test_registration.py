from .support import (
    AppError,
    INSTITUTION_A,
    _active_institution_authorization,
    _envelope,
    _registration_payload,
    client,
    patch,
)


def test_institution_lookup_is_public_and_returns_the_safe_projection():
    payload = {
        "institution_id": INSTITUTION_A,
        "code": "GIT",
        "name": "Greenfield Institute of Technology",
    }
    with patch(
        "app.api.platform.institutions.lookup_institution_by_code", return_value=payload
    ):
        # No Authorization header: discovery must work before login.
        response = client.get("/api/v1/institutions/lookup", params={"code": "GIT"})
    assert response.status_code == 200
    body = response.json()
    # Phase 6.15.2 â€” exactly {institution_id, code, name}; nothing else leaks.
    assert set(body) == {"institution_id", "code", "name"}
    assert body["institution_id"] == INSTITUTION_A


def test_unknown_institution_code_fails_safely():
    with patch(
        "app.api.platform.institutions.lookup_institution_by_code",
        side_effect=AppError(
            "Institution not found", status_code=404, code="INSTITUTION_NOT_FOUND"
        ),
    ):
        response = client.get("/api/v1/institutions/lookup", params={"code": "NO-SUCH"})
    assert response.status_code == 404
    assert _envelope(response)["code"] == "INSTITUTION_NOT_FOUND"


def test_institution_lookup_has_no_authentication_dependency():
    from app.api.platform import institutions as institutions_api

    # APIRouter(prefix="/institutions") prepends the prefix when the route is
    # added, so the stored path is "/institutions/lookup", not "/lookup".
    route = next(
        r
        for r in institutions_api.router.routes
        if getattr(r, "path", "").endswith("/lookup")
    )
    dependency_names = {
        getattr(d.call, "__name__", "") for d in route.dependant.dependencies
    }
    assert "get_current_user" not in dependency_names


def test_registration_requires_institution_and_academic_identifier():
    missing_institution = _registration_payload()
    missing_institution.pop("institution_id")
    assert (
        client.post("/api/v1/registration", json=missing_institution).status_code == 422
    )

    with patch(
        "app.api.auth.registration.register_student",
        side_effect=AppError(
            "Provide at least one of register_number or university_roll_number",
            status_code=422,
            code="IDENTIFIER_REQUIRED",
        ),
    ):
        response = client.post(
            "/api/v1/registration",
            json=_registration_payload(
                register_number=None, university_roll_number=None
            ),
        )
    assert response.status_code == 422
    assert _envelope(response)["code"] == "IDENTIFIER_REQUIRED"


def test_registration_never_reports_success_for_a_failed_service_call():
    with patch(
        "app.api.auth.registration.register_student",
        side_effect=AppError(
            "Unable to complete registration at this time. Please try again later.",
            status_code=500,
            code="REGISTRATION_FAILED",
        ),
    ):
        response = client.post("/api/v1/registration", json=_registration_payload())
    assert response.status_code == 500
    assert _envelope(response)["code"] == "REGISTRATION_FAILED"
