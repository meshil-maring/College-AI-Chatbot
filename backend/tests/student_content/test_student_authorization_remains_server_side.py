from .support import (
    NOTICE_A,
    RESOURCE_A,
    _clear_dependency_overrides,
    _student_user,
    app,
    client,
    get_current_user,
)


class TestStudentAuthorizationRemainsServerSide:
    def test_student_cannot_list_admin_notices(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/admin/notices")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_create_update_or_delete_notices(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        created = client.post(
            "/api/v1/admin/notices", json={"title": "t", "content": "c"}
        )
        updated = client.patch(
            f"/api/v1/admin/notices/{NOTICE_A}", json={"title": "t2"}
        )
        deleted = client.delete(f"/api/v1/admin/notices/{NOTICE_A}")
        for response in (created, updated, deleted):
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_publish_an_admin_faq(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.post(f"/api/v1/admin/faqs/{RESOURCE_A}/publish")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_student_cannot_ingest_or_read_documents(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        ingest = client.post("/api/v1/documents/ingest", json={})
        listing = client.get(f"/api/v1/admin/knowledge-sources/{RESOURCE_A}/documents")
        assert ingest.status_code == 403
        assert listing.status_code == 403

    def test_student_cannot_read_the_admin_dashboard(self):
        app.dependency_overrides[get_current_user] = lambda: _student_user()
        response = client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403

    def test_there_is_no_student_mutation_route_for_notices_or_resources(self):
        """Only GET is registered on the two new student paths."""
        paths = app.openapi()["paths"]
        assert "get" in paths["/api/v1/students/me/notices"]
        assert "get" in paths["/api/v1/students/me/resources"]
        for method in ("post", "patch", "put", "delete"):
            assert method not in paths["/api/v1/students/me/notices"]
            assert method not in paths["/api/v1/students/me/resources"]
