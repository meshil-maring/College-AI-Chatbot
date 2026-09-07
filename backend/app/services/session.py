"""Request-scoped session identity resolution."""

from uuid import UUID, uuid4

from app.schemas.session import (
    SessionContext,
    SessionContextRequest,
    SessionContextResponse,
)


def resolve_session_context(request: SessionContextRequest) -> SessionContext:
    """Create or validate the session identity for one chat request."""
    if not isinstance(request, SessionContextRequest):
        raise TypeError("request must be a validated SessionContextRequest")

    return SessionContext(session_id=request.session_id or uuid4())


def session_response(context: SessionContext) -> SessionContextResponse:
    """Create the public session contract without exposing implementation details."""
    if not isinstance(context, SessionContext):
        raise TypeError("context must be a validated SessionContext")

    return SessionContextResponse(session_id=context.session_id)


def resolve_session_id(session_id: UUID | str | None = None) -> UUID:
    """Resolve a session ID for integrations that already receive a raw value."""
    request = SessionContextRequest(session_id=session_id)
    return resolve_session_context(request).session_id