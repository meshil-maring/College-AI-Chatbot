from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.academics.semester_registration import router
from app.core.security import get_current_user
from app.services.academics import semester_registration as service


def test_student_completion_passes_only_validated_option_ids():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    user = {"user_id": str(uuid4())}
    app.dependency_overrides[get_current_user] = lambda: user
    registration_id, option_id = str(uuid4()), str(uuid4())
    url = f"/api/v1/students/me/semester-registrations/{registration_id}/complete"
    with TestClient(app) as client, patch.object(service, "complete", return_value={"status": "registered"}) as writer:
        assert client.post(url, json={"selected_option_ids": [option_id]}).status_code == 200
        writer.assert_called_once_with(user, registration_id, [option_id])
        for field in ("student_id", "institution_id", "academic_section_id"):
            assert client.post(url, json={"selected_option_ids": [option_id], field: str(uuid4())}).status_code == 422
        assert writer.call_count == 1
