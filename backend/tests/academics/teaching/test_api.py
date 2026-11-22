from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.academics.teaching_assignments import _ACTOR, router
from app.core.application_routes import register_feature_routes
from app.services.academics import teaching_assignments as service


def client_for(user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[_ACTOR] = lambda: user
    return TestClient(app)


def test_routes_are_mounted_for_the_application():
    app = FastAPI()
    register_feature_routes(app)
    paths = set(app.openapi()["paths"])
    assert {"/api/v1/teaching-assignments", "/api/v1/teaching-assignments/options",
            "/api/v1/teaching-assignments/{assignment_id}/decision",
            "/api/v1/teaching-assignments/{assignment_id}/end"} <= paths


def test_reads_go_to_the_service_with_the_authenticated_user():
    user = {"user_id": str(uuid4())}
    with (
        client_for(user) as client,
        patch.object(service, "overview", return_value={"assignments": []}) as overview,
        patch.object(service, "options", return_value={"offerings": []}) as options,
    ):
        assert client.get("/api/v1/teaching-assignments").json() == {"assignments": []}
        assert client.get("/api/v1/teaching-assignments/options").status_code == 200
    overview.assert_called_once_with(user)
    options.assert_called_once_with(user)


def test_request_accepts_only_offering_teacher_and_dates():
    user, offering, faculty = {"user_id": str(uuid4())}, uuid4(), uuid4()
    body = {"academic_offering_id": str(offering), "faculty_user_id": str(faculty)}
    with client_for(user) as client, patch.object(service, "request", return_value={}) as writer:
        assert client.post("/api/v1/teaching-assignments", json=body).status_code == 201
        for field in ("department_id", "institution_id", "status", "needs_approval"):
            assert client.post("/api/v1/teaching-assignments", json={**body, field: "x"}).status_code == 422
        reversed_term = {**body, "starts_on": "2026-12-10", "planned_end_on": "2026-12-01"}
        assert client.post("/api/v1/teaching-assignments", json=reversed_term).status_code == 422
    writer.assert_called_once_with(user, {
        "academic_offering_id": offering, "faculty_user_id": faculty, "starts_on": None, "planned_end_on": None,
    })


def test_decision_needs_a_known_action_and_a_reason_to_reject():
    user, assignment = {"user_id": str(uuid4())}, str(uuid4())
    url = f"/api/v1/teaching-assignments/{assignment}/decision"
    with client_for(user) as client, patch.object(service, "decide", return_value={}) as writer:
        assert client.post(url, json={"action": "approve"}).status_code == 200
        assert client.post(url, json={"action": "reject", "note": "   "}).status_code == 422
        assert client.post(url, json={"action": "reject", "note": " Clash "}).status_code == 200
        assert client.post(url, json={"action": "end"}).status_code == 422
        assert client.post(url, json={"action": "approve", "as_admin": True}).status_code == 422
    assert [call.args for call in writer.call_args_list] == [
        (user, assignment, "approve", None), (user, assignment, "reject", "Clash"),
    ]


def test_end_passes_the_path_identifier_only():
    user, assignment = {"user_id": str(uuid4())}, str(uuid4())
    with client_for(user) as client, patch.object(service, "end", return_value={}) as writer:
        assert client.post(f"/api/v1/teaching-assignments/{assignment}/end").status_code == 200
        assert client.post("/api/v1/teaching-assignments/not-a-uuid/end").status_code == 422
    writer.assert_called_once_with(user, assignment)
