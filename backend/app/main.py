"""Application entry point and authenticated/public generation boundaries."""
import logging
import time
import httpx
import uvicorn
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.errors import AppError
from app.core.application import create_application
from app.core.application_routes import register_feature_routes
from app.core.operational_routes import register_operational_routes
from app.core.security import require_permission, require_institution_roles, scope_tenant
from app.db.supabase import get_admin_client
from app.api.ai.public_contract import PUBLIC_CHAT_RESPONSES
from app.schemas.ai.chat import AuthenticatedChatRequest, ChatRequest, ChatResponse, PublicChatRequest, PublicChatResponse
from app.schemas.ai.session import SessionContextRequest
from app.services.ai.chat import process_chat_request
from app.services.ai.turns.workflow import run as run_chat_turn
from app.api.ai.chat_turns import router as chat_turn_router
from app.services.knowledge.resources.public_chat import process_public_request
from app.services.ai.generation_provider import OpenRouterGenerationProvider
from app.services.auth.session import resolve_session_context
from app.services.auth.public_abuse_controls import acquire_concurrency, enforce_rate_limit

logger = logging.getLogger(__name__)
app = create_application(settings)
register_feature_routes(app)
app.include_router(chat_turn_router, prefix='/api/v1')
register_operational_routes(app, settings, lambda: get_admin_client())

generation_router = APIRouter(prefix="/generation", tags=["generation"])

# Phase 7.22: authenticated AI is an institution capability. Reuse the Phase
# 7.20 authorization context so a tenant-less or inactive staff/faculty account
# cannot be mistaken for a platform principal by the legacy `scope_tenant`
# helper and select an institution in the request body.
_INSTITUTION_CHAT = require_institution_roles("admin", "staff", "faculty", "student")


@generation_router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_permission("ai.chat"))],
)
def chat(
    request: AuthenticatedChatRequest,
    current_user: dict = Depends(_INSTITUTION_CHAT),
) -> ChatResponse:
    """Process one chat request with persistent conversation and message records.

    Tenant isolation: an active institution grant is resolved before this
    handler runs, and the client-supplied ``institution_id`` must match it.
    A principal of College A can never retrieve College B's knowledge;
    missing/inactive scope fails closed and a mismatch returns 403.
    """
    tenant_id = scope_tenant(current_user, request.institution_id)
    if tenant_id is None:
        raise AppError("Institution scope required", 403, "SCOPE_MISSING")
    internal_request = ChatRequest(
        user_query=request.user_query,
        session_id=request.session_id,
        conversation_id=request.conversation_id,
        institution_id=tenant_id,
        resource_id=request.resource_id,
        turn_id=request.turn_id,
    )
    session_context = resolve_session_context(
        SessionContextRequest(session_id=request.session_id)
    )
    response = run_chat_turn(
        internal_request,
        session_context,
        OpenRouterGenerationProvider(),
        user_id=current_user["user_id"],
        current_user=current_user,
        process=process_chat_request,
    )
    # Provider/model identifiers and internal diagnostics are not a normal
    # chat capability; this route has no separately authorized debug projection.
    return response.model_copy(update={"model_used": None, "metadata": {}})

app.include_router(generation_router, prefix="/api/v1")

# ============================================================================
# Public, unauthenticated college chat
# ============================================================================
# General and casual messages can use direct generation. College-specific
# questions use only policy-authorized public knowledge. Personal-data requests
# still require authentication, and no authentication dependency is attached
# to this anonymous endpoint by design.

public_chat_router = APIRouter(prefix="/chat", tags=["chat"])


@public_chat_router.post(
    "/public",
    response_model=PublicChatResponse,
    summary="Ask the public college chatbot",
    description=(
        "Authentication: Not required. Resolves the public institution code "
        "server-side. Casual and general questions are answered directly; "
        "college-specific questions use only policy-authorized public knowledge. "
        "Personal-data requests require authentication. Responses are stateless "
        "and omit internal identifiers and diagnostics."
    ),
    responses=PUBLIC_CHAT_RESPONSES,
)
def public_chat(request: PublicChatRequest, http_request: Request) -> PublicChatResponse:
    """Process one public, stateless AI chat request.

    Phase 7.3:
      * no authentication dependency — public AI requires no login;
      * the public institution code is resolved and validated server-side;
      * the strict request model exposes no retrieval identifiers or controls;
      * intent determines whether direct generation or public RAG is needed;
      * retrieval and final provenance verification require explicit public
        visibility plus valid source/version/processing lifecycle state;
      * the response projection exposes no internal IDs, model data, usage,
        diagnostics, or authorization metadata;
      * personal-data questions from an unauthenticated caller are rejected
        with the standard 401 AUTH_REQUIRED error.
      * requests are stateless and create no anonymous conversation history.
    """
    # Identity is the direct peer socket address. Forwarding headers are
    # deliberately ignored because this repository has no trusted-proxy
    # configuration; accepting them would create a trivial spoofing bypass.
    client_identity = (
        http_request.client.host if http_request.client is not None else "unknown"
    )
    enforce_rate_limit(client_identity, request.institution_code)
    lease = acquire_concurrency(request.institution_code)
    started_at = time.perf_counter()
    status = 200
    try:
        session_context = resolve_session_context(SessionContextRequest())
        return process_public_request(
            request,
            session_context,
            OpenRouterGenerationProvider(
                timeout=settings.public_generation_timeout_seconds,
            ),
        )
    except AppError as exc:
        status = exc.status_code
        raise
    except httpx.TransportError:
        status = 503
        logger.warning("event=public_chat_failed status=503 category=dependency_unavailable")
        raise AppError(
            "The chatbot is temporarily unavailable. Please try again shortly.",
            status_code=503,
            code="PUBLIC_CHAT_UNAVAILABLE",
            headers={"Retry-After": "5"},
        ) from None
    except Exception:
        status = 500
        # This public boundary deliberately records only coarse metadata.
        # Exception text can contain provider/database diagnostics and must not
        # be copied into production logs for an unauthenticated request.
        logger.error(
            "event=public_chat_failed institution=%s status=500 category=internal",
            request.institution_code,
        )
        raise AppError(
            "An unexpected server error occurred. Please try again later.",
            status_code=500,
            code="INTERNAL_ERROR",
        ) from None
    finally:
        lease.release()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "event=public_chat_request institution=%s status=%s duration_ms=%s",
            request.institution_code,
            status,
            duration_ms,
        )

app.include_router(public_chat_router, prefix="/api/v1")



def start():
    """Console-script entry point (``uv run start``).

    Binds to ``0.0.0.0`` so the API is also reachable from other devices on the
    local network, but prints the *browsable* localhost URLs. ``0.0.0.0`` is a
    bind address, not a destination — opening it in a browser always fails, and
    the uvicorn banner alone made the backend look broken.
    """
    host = "0.0.0.0"
    port = 8000
    if settings.is_local_environment:
        print(f"Backend (UI entry point):  http://localhost:5173  (frontend dev server)")
        print(f"API root:                  http://127.0.0.1:{port}/")
        if settings.effective_api_docs_enabled:
            print(f"API docs (Swagger UI):     http://127.0.0.1:{port}/docs")
        print(f"Health check:              http://127.0.0.1:{port}/health")
        print(f"Readiness check:           http://127.0.0.1:{port}/ready")
        print(f"Note: {host}:{port} is the bind address and is NOT browsable.\n")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=settings.is_local_environment,
        workers=1,
        proxy_headers=False,
    )
