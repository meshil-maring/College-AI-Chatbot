from .support import (
    TENANT_A,
    STUDENT_USER_ID,
    _FakeClient,
    _clear_dependency_overrides,
    dashboard_repo,
    _resource_row,
)


class TestRepositoryProjections:
    def test_notice_projection_excludes_tenant_and_audit_columns(self):
        database = _FakeClient({"notices": []})
        dashboard_repo.list_published_notices(database, TENANT_A)
        projection = database.operations("notices", "select")[0][2]
        for forbidden in ("institution_id", "created_by", "updated_at"):
            assert forbidden not in projection

    def test_resource_projection_excludes_storage_and_identity_columns(self):
        database = _FakeClient({'knowledge_sources': [_resource_row()]})
        projection = dashboard_repo.list_published_resources(database, TENANT_A, actor_user_id=STUDENT_USER_ID)[0]
        for forbidden in (
            "storage_bucket",
            "storage_object_key",
            "file_checksum",
            "created_by_user_id",
            "institution_id",
            "document_id",
        ):
            assert forbidden not in projection

    def test_resource_projection_selects_only_benign_labels(self):
        database = _FakeClient({'knowledge_sources': [_resource_row()]})
        projection = dashboard_repo.list_published_resources(database, TENANT_A, actor_user_id=STUDENT_USER_ID)[0]
        for expected in (
            "knowledge_source_id",
            "source_type",
            "title",
            "description",
            "lifecycle_status",
            "effective_from",
            "effective_until",
        ):
            assert expected in projection
