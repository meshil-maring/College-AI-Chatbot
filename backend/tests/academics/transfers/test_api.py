from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.academics.student_transfers import _ADMIN, _REVIEWER, router
from app.core.security import get_current_user
from app.services.academics import student_transfers as service


def client_for(user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    for dependency in (get_current_user, _REVIEWER, _ADMIN):
        app.dependency_overrides[dependency] = lambda: user
    return TestClient(app)


def test_student_submission_rejects_browser_supplied_identity_and_placement():
    user, section = {"user_id": str(uuid4())}, str(uuid4())
    url = "/api/v1/students/me/transfer-requests"
    body = {"to_section_id": section, "reason": "  Clash with my part-time job  "}
    with client_for(user) as client, patch.object(service, "submit", return_value={}) as writer:
        assert client.post(url, json=body).status_code == 201
        writer.assert_called_once_with(user, {"to_section_id": section, "reason": "Clash with my part-time job"})
        for field in ("student_id", "institution_id", "from_section_id", "status"):
            assert client.post(url, json={**body, field: str(uuid4())}).status_code == 422
        assert client.post(url, json={**body, "reason": "short"}).status_code == 422
        assert client.post(url, json={**body, "reason": " " * 20}).status_code == 422
    assert writer.call_count == 1


def test_cancel_passes_path_identifier_only():
    user, request = {"user_id": str(uuid4())}, str(uuid4())
    with client_for(user) as client, patch.object(service, "cancel", return_value={}) as writer:
        assert client.post(f"/api/v1/students/me/transfer-requests/{request}/cancel").status_code == 200
        assert client.post("/api/v1/students/me/transfer-requests/not-a-uuid/cancel").status_code == 422
    writer.assert_called_once_with(user, request)


def test_review_queue_status_filter_is_closed():
    user = {"user_id": str(uuid4())}
    with client_for(user) as client, patch.object(service, "reviews", return_value={}) as reader:
        assert client.get("/api/v1/transfer-reviews").status_code == 200
        assert client.get("/api/v1/transfer-reviews?status=all").status_code == 200
        assert client.get("/api/v1/transfer-reviews?status=approved").status_code == 422
    assert [call.args[1] for call in reader.call_args_list] == [True, False]


def test_decision_accepts_only_known_actions():
    user, request = {"user_id": str(uuid4())}, str(uuid4())
    url = f"/api/v1/transfer-reviews/{request}/decision"
    with client_for(user) as client, patch.object(service, "decide", return_value={}) as writer:
        assert client.post(url, json={"action": "approve"}).status_code == 200
        assert client.post(url, json={"action": "complete"}).status_code == 422
        assert client.post(url, json={"action": "approve", "decided_as": "admin"}).status_code == 422
    writer.assert_called_once_with(user, request, {"action": "approve", "comment": None})


def test_department_head_can_be_assigned_or_removed():
    user, department, faculty = {"user_id": str(uuid4())}, str(uuid4()), str(uuid4())
    url = f"/api/v1/admin/department-heads/{department}"
    with client_for(user) as client, patch.object(service, "assign_department_head", return_value={}) as writer:
        assert client.put(url, json={"faculty_user_id": faculty}).status_code == 200
        assert client.put(url, json={"faculty_user_id": None}).status_code == 200
        assert client.put(url, json={}).status_code == 422
    assert [call.args[1:] for call in writer.call_args_list] == [(department, faculty), (department, None)]


def test_direct_transfer_names_student_but_never_tenant_or_source():
    user, student, section = {"user_id": str(uuid4())}, str(uuid4()), str(uuid4())
    body = {"student_id": student, "to_section_id": section, "reason": "Moved to balance section sizes"}
    with client_for(user) as client, patch.object(service, "direct_transfer", return_value={}) as writer:
        assert client.post("/api/v1/transfer-direct", json=body).status_code == 201
        for field in ("institution_id", "from_section_id", "initiated_by", "status"):
            assert client.post("/api/v1/transfer-direct", json={**body, field: str(uuid4())}).status_code == 422
        assert client.post("/api/v1/transfer-direct", json={**body, "reason": "short"}).status_code == 422
    writer.assert_called_once_with(user, {**body, "allow_other_semester": False})


def test_direct_transfer_forwards_explicit_semester_override():
    user = {"user_id": str(uuid4())}
    body = {"student_id": str(uuid4()), "to_section_id": str(uuid4()),
            "reason": "Lateral entry approved by the board", "allow_other_semester": True}
    with client_for(user) as client, patch.object(service, "direct_transfer", return_value={}) as writer:
        assert client.post("/api/v1/transfer-direct", json=body).status_code == 201
        assert client.post("/api/v1/transfer-direct", json={**body, "allow_other_semester": "maybe"}).status_code == 422
    writer.assert_called_once_with(user, body)


def test_direct_transfer_reads_use_reviewer_scope():
    user, student = {"user_id": str(uuid4())}, str(uuid4())
    with (
        client_for(user) as client,
        patch.object(service, "direct_students", return_value={}) as students,
        patch.object(service, "direct_options", return_value={}) as options,
    ):
        assert client.get("/api/v1/transfer-direct/students").status_code == 200
        assert client.get(f"/api/v1/transfer-direct/students/{student}").status_code == 200
        assert client.get("/api/v1/transfer-direct/students/not-a-uuid").status_code == 422
    students.assert_called_once_with(user)
    options.assert_called_once_with(user, student)
