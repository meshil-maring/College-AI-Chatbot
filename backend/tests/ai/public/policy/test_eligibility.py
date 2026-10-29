from .support import (
    AppError,
    DOC,
    FakeClient,
    INST_A,
    INST_B,
    KS_PRIVATE,
    KS_PUBLIC,
    PublicChatRequest,
    RUN,
    UUID,
    _build_allowed_public_knowledge_source_ids,
    date,
    is_public_provenance,
    is_public_source,
    provenance,
    pytest,
    source,
)

@pytest.mark.parametrize("visibility", ["authenticated", "restricted", None])
def test_non_public_visibility_is_denied(visibility):
    assert not is_public_source(
        source(visibility=visibility), INST_A, on_date=date(2026, 9, 28)
    )

def test_public_source_requires_same_tenant_publication_and_effective_window():
    today = date(2026, 9, 28)
    assert is_public_source(source(), INST_A, on_date=today)
    assert not is_public_source(source(), INST_B, on_date=today)
    assert not is_public_source(
        source(lifecycle_status="draft"), INST_A, on_date=today
    )
    assert not is_public_source(
        source(effective_from="2026-09-29"), INST_A, on_date=today
    )
    assert not is_public_source(
        source(effective_until="2026-09-27"), INST_A, on_date=today
    )

@pytest.mark.parametrize("status", ["archived", "deleted", "revoked", "superseded"])
def test_invalid_source_lifecycle_is_denied(status):
    assert not is_public_source(
        source(lifecycle_status=status), INST_A, on_date=date(2026, 9, 28)
    )

def test_complete_provenance_policy_allows_only_valid_version_and_processing():
    today = date(2026, 9, 28)
    assert is_public_provenance(provenance(), INST_A, on_date=today)

    invalid_version = provenance()
    invalid_version["document_version"]["lifecycle_status"] = "draft"
    assert not is_public_provenance(invalid_version, INST_A, on_date=today)

    failed = provenance(processing_status="failed")
    assert not is_public_provenance(failed, INST_A, on_date=today)
    incomplete = provenance(embedding_status="processing")
    assert not is_public_provenance(incomplete, INST_A, on_date=today)
    no_completion = provenance(completed_at=None)
    assert not is_public_provenance(no_completion, INST_A, on_date=today)

def test_explicit_source_authorization_is_non_enumerating():
    fake = FakeClient(
        {
            "knowledge_sources": [
                source(),
                source(
                    knowledge_source_id=KS_PRIVATE,
                    visibility="restricted",
                ),
            ]
        }
    )
    assert _build_allowed_public_knowledge_source_ids(fake, UUID(INST_A), KS_PUBLIC) == {
        KS_PUBLIC
    }
    for source_id in (KS_PRIVATE, "30000000-0000-0000-0000-000000000099"):
        with pytest.raises(AppError) as exc:
            _build_allowed_public_knowledge_source_ids(fake, UUID(INST_A), source_id)
        assert exc.value.code == "KNOWLEDGE_SOURCE_NOT_PUBLIC"
        assert exc.value.status_code == 403

def test_strict_public_request_rejects_internal_controls():
    valid = PublicChatRequest(institution_code=" git ", message="  What courses? ")
    assert valid.institution_code == "GIT"
    assert valid.message == "What courses?"
    for field, value in (
        ("knowledge_source_id", KS_PUBLIC),
        ("document_id", DOC),
        ("processing_run_id", RUN),
        ("model_name", "attacker/model"),
        ("retrieved_chunks", []),
        ("debug", True),
    ):
        with pytest.raises(Exception):
            PublicChatRequest(
                institution_code="GIT", message="Question", **{field: value}
            )
