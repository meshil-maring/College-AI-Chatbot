"""Phase 6.15.2 — Public institution lookup endpoint tests.

Covers GET /api/v1/institutions/lookup: valid code, invalid/unknown code,
empty/short code, inactive institution, and the SAFE response projection
(only institution_id / code / name — never contact/location/organization/
status/join-code/internal fields). No authentication is required by design:
this endpoint exists for the unauthenticated student registration form.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

INST_A = "b0000000-0000-0000-0000-0000000000a1"
ORG_A = "a0000000-0000-0000-0000-00000000000a"


def inst_row(**over):
    row = {
        "institution_id": INST_A,
        "organization_id": ORG_A,
        "name": "Imphal College",
        "code": "IMPHAL",
        "email": "office@imphal.example.com",
        "address": "123 Campus Road",
        "city": "Imphal",
        "state": "Manipur",
        "country": "India",
        "status": "active",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(over)
    return row


def fake_db(institution: dict | None):
    db = MagicMock()
    response = MagicMock()
    response.data = institution
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value
    ) = response
    return db


def test_valid_institution_code_resolves():
    with patch(
        "app.services.tenancy.get_admin_client", return_value=fake_db(inst_row())
    ):
        r = client.get("/api/v1/institutions/lookup", params={"code": "IMPHAL"})
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "institution_id": INST_A,
        "code": "IMPHAL",
        "name": "Imphal College",
    }


def test_code_lookup_is_case_insensitive_and_normalized():
    with patch(
        "app.services.tenancy.get_admin_client", return_value=fake_db(inst_row())
    ) as mocked:
        r = client.get("/api/v1/institutions/lookup", params={"code": "  imphal "})
    assert r.status_code == 200
    db = mocked.return_value
    eq_call = db.table.return_value.select.return_value.eq
    eq_call.assert_called_once_with("code", "IMPHAL")


def test_unknown_code_is_404_not_found():
    with patch(
        "app.services.tenancy.get_admin_client", return_value=fake_db(None)
    ):
        r = client.get("/api/v1/institutions/lookup", params={"code": "NOPE99"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "INSTITUTION_NOT_FOUND"


def test_short_code_is_rejected_with_validation_error():
    r = client.get("/api/v1/institutions/lookup", params={"code": "A"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_code_is_rejected_with_validation_error():
    r = client.get("/api/v1/institutions/lookup")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_blank_code_is_rejected_with_validation_error():
    with patch("app.services.tenancy.get_admin_client") as mocked:
        r = client.get("/api/v1/institutions/lookup", params={"code": "   "})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    mocked.assert_not_called()


def test_inactive_institution_is_not_joinable():
    with patch(
        "app.services.tenancy.get_admin_client",
        return_value=fake_db(inst_row(status="pending", is_active=False)),
    ):
        r = client.get("/api/v1/institutions/lookup", params={"code": "IMPHAL"})
    assert r.status_code == 403
    assert (
        r.json()["error"]["code"] == "INSTITUTION_NOT_ACCEPTING_REGISTRATIONS"
    )


def test_response_exposes_only_safe_public_fields():
    with patch(
        "app.services.tenancy.get_admin_client", return_value=fake_db(inst_row())
    ):
        r = client.get("/api/v1/institutions/lookup", params={"code": "IMPHAL"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"institution_id", "code", "name"}
    for forbidden in (
        "email",
        "address",
        "city",
        "state",
        "country",
        "status",
        "is_active",
        "organization_id",
        "join_code",
        "created_at",
        "updated_at",
    ):
        assert forbidden not in body


def test_lookup_requires_no_authentication():
    # The endpoint is deliberately public: no Authorization header is sent.
    with patch(
        "app.services.tenancy.get_admin_client", return_value=fake_db(inst_row())
    ):
        r = client.get(
            "/api/v1/institutions/lookup",
            params={"code": "IMPHAL"},
            headers={"Authorization": ""},
        )
    assert r.status_code == 200
