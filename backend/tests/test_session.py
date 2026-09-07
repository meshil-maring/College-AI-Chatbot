"""Focused tests for Phase 4.1 session context."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.session import SessionContext, SessionContextRequest
from app.services.session import resolve_session_context, resolve_session_id, session_response


def test_missing_session_id_creates_a_valid_uuid() -> None:
    context = resolve_session_context(SessionContextRequest())

    assert isinstance(context.session_id, UUID)
    assert context.session_id.version == 4


def test_valid_session_id_is_preserved() -> None:
    session_id = uuid4()

    context = resolve_session_context(SessionContextRequest(session_id=session_id))

    assert context.session_id == session_id
    assert session_response(context).session_id == session_id


def test_invalid_session_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SessionContextRequest(session_id="not-a-uuid")


def test_raw_session_id_adapter_validates_and_preserves_identity() -> None:
    session_id = uuid4()

    assert resolve_session_id(str(session_id)) == session_id


def test_session_context_requires_a_valid_uuid() -> None:
    with pytest.raises(ValidationError):
        SessionContext(session_id="not-a-uuid")


def test_resolver_does_not_persist_messages() -> None:
    context = resolve_session_context(SessionContextRequest())

    assert context.model_dump() == {"session_id": context.session_id}
    assert not hasattr(context, "messages")