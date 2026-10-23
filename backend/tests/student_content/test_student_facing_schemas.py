from .support import (
    NOTICE_A,
    RESOURCE_A,
    StudentNotice,
    StudentNoticeList,
    StudentResource,
    StudentResourceList,
    TENANT_A,
    _clear_dependency_overrides,
    pytest,
)


class TestStudentFacingSchemas:
    def test_notice_contract_has_no_tenant_or_internal_user_fields(self):
        assert set(StudentNotice.model_fields) == {
            "notice_id",
            "title",
            "content",
            "category",
            "priority",
            "is_pinned",
            "published_at",
            "expires_at",
        }

    def test_resource_contract_has_no_storage_or_tenant_fields(self):
        assert set(StudentResource.model_fields) == {
            "resource_id",
            "title",
            "description",
            "source_type",
            "effective_from",
            "effective_until",
        }

    def test_list_contracts_reject_extra_fields(self):
        with pytest.raises(Exception):
            StudentNoticeList(items=[], total=0, institution_id=TENANT_A)
        with pytest.raises(Exception):
            StudentResourceList(items=[], total=0, storage_object_key="x")

    def test_models_reject_smuggled_internal_identifiers(self):
        with pytest.raises(Exception):
            StudentNotice(
                notice_id=NOTICE_A,
                title="t",
                content="c",
                category="general",
                priority="normal",
                institution_id=TENANT_A,
            )
        with pytest.raises(Exception):
            StudentResource(
                resource_id=RESOURCE_A,
                title="t",
                source_type="handbook",
                storage_object_key="institution/handbook.pdf",
            )
