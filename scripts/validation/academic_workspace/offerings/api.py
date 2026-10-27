"""Real FastAPI routes backed by the configured database and resolved admin."""

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app


STRUCTURE_URL = "/api/v1/admin/academic-structure"
BASE_URL = "/api/v1/admin/academic-setup"


@contextmanager
def administrator_api(user):
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client
    finally:
        client.close()
        if previous is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous


def create_offering(client, payload):
    response = client.post(f"{STRUCTURE_URL}/academic_offerings", json=payload)
    if response.status_code != 201:
        raise RuntimeError(f"Real offering API creation failed: {response.status_code} {response.text}")
    return response.json()
