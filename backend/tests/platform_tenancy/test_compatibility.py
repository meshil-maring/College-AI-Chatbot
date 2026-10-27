"""Organization and institution foundation regressions: compatibility."""

from __future__ import annotations

from .support import (
    INST_A1,
    INST_A2,
    MagicMock,
    SafeAuthFailure,
    USER_ID,
    UUID,
    _assert_institution_active,
    _expect,
    inspect,
    patch,
    public_chat,
    pytest,
    scope_tenant,
)


def test_locked_tenant_helpers_still_reject_cross_institution() -> None:
    tenant_a = {"user_id": USER_ID, "roles": ["student"], "institution_id": INST_A1}
    assert scope_tenant(tenant_a, INST_A1) == UUID(INST_A1)
    _expect("TENANT_MISMATCH", scope_tenant, tenant_a, INST_A2)


def test_student_authentication_still_gated_by_institution_is_active() -> None:
    with patch(
        "app.services.auth.student_auth._get_institution",
        return_value={"is_active": True},
    ):
        _assert_institution_active(MagicMock(), UUID(INST_A1))

    for inactive in ({"is_active": False}, None):
        with patch("app.services.auth.student_auth._get_institution", return_value=inactive):
            with pytest.raises(SafeAuthFailure):
                _assert_institution_active(MagicMock(), UUID(INST_A1))


def test_public_chat_requires_no_authentication() -> None:
    source = inspect.getsource(public_chat)
    assert "PUBLIC_USER_ID" in source
    assert "get_current_user" not in source
    assert "verify_jwt" not in source
    assert list(inspect.signature(public_chat.process_chat_request).parameters) == [
        "request",
        "context",
        "provider",
    ]


def test_public_chat_owns_every_public_turn_with_public_user_id() -> None:
    source = inspect.getsource(public_chat.process_chat_request)
    assert "user_id = PUBLIC_USER_ID" in source


def test_public_chat_institution_id_is_now_validated_server_side() -> None:
    """Phase 6.13.8: the public path now validates institution_id before use.

    The prior known limitation (public chat accepted institution_id but did not
    enforce institution-specific RAG filtering) is closed in this phase:

    * the client-supplied institution_id is validated server-side by
      ``_validate_public_institution`` (exists, ACTIVE, belongs to a valid org),
    * the validated institution is used as the retrieval scope,
    * retrieved chunks are post-filtered at the data-access boundary to
      public knowledge sources only (``_filter_to_public_chunks``), so
      private / student / cross-institution documents can never enter the LLM
      context,
    * client-supplied scope overrides (``knowledge_source_id`` that belongs to
      another institution or is non-public) are rejected at the validation
      boundary.

    The public path still owns every turn with ``PUBLIC_USER_ID`` (unchanged
    invariant) — the additions are additive guards around the existing pipeline,
    not a redesign.
    """
    source = inspect.getsource(public_chat.process_chat_request)
    assert "institution_id=request.institution_id" in source
    # The public path now validates the institution before use.
    assert "_validate_public_institution" in source
    # Phase 7.2 re-verifies full source/version/run/chunk provenance.
    assert "PublicKnowledgePolicy" in source
    assert "authorize_chunks" in source
    # The public path rejects personal-data questions.
    assert "_reject_personal_query_if_needed" in source


def test_public_chat_is_now_exposed_as_an_http_route() -> None:
    """Phase 6.13.8: public chat is exposed at POST /api/v1/chat/public.

    The public chat service (``app.services.ai.public_chat.process_chat_request``)
    was already wired in Phase 6.13.1; this phase adds the unauthenticated
    HTTP route so public AI is reachable without a login, while the protected
    endpoint remains ``POST /api/v1/generation/chat`` (authenticated).
    """
    from app.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    # FastAPI 0.141+ uses lazy _IncludedRouter expansion; the public route
    # may not appear in app.routes until the OpenAPI schema is built.
    if not any("public" in p for p in paths):
        schema = app.openapi()
        paths.update(schema.get("paths", {}).keys())
    public_paths = {path for path in paths if "public" in path}
    assert public_paths, (
        "Phase 6.13.8 must expose the public chat route. "
        "The project convention is POST /api/v1/chat/public."
    )
    # The route must be present; verify it is a chat-style path rather than an
    # unrelated admin/internal path.
    assert any("/chat" in path for path in public_paths), (
        public_paths
    )
