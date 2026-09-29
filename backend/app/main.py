import logging
import time

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user, resolve_primary_role, scope_tenant
from app.api.ingestion import router as ingestion_router
from app.api.auth import router as auth_router
from app.api.registration import router as registration_router
from app.api.conversations import router as conversations_router
from app.api.admin import router as admin_router
from app.api.organizations import router as organizations_router
from app.api.institutions import router as institutions_router
from app.api.users import router as users_router
from app.api.student_auth import router as student_auth_router
from app.api.students import router as students_router
from app.api.student_notifications import router as student_notifications_router
from app.api.dev_auth import router as dev_auth_router
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    PublicAPIErrorResponse,
    PublicChatRequest,
    PublicChatResponse,
)
from app.schemas.session import SessionContextRequest
from app.services.chat import process_chat_request
from app.services.public_chat import process_public_request
from app.services.generation_provider import OpenRouterGenerationProvider
from app.services.session import resolve_session_context
from app.core.startup_validation import run_startup_configuration_validation
from app.middleware.public_body_limit import PublicChatBodyLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.db.supabase import get_admin_client
from app.services.public_abuse_controls import (
    acquire_concurrency,
    enforce_rate_limit,
)

# Phase 6.15.8 — fail fast on an invalid/incomplete deployment configuration.
# In local development/testing this only logs a warning; anywhere else a
# failed check stops startup with a value-free error message.
run_startup_configuration_validation(settings)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.effective_api_docs_enabled else None,
    redoc_url="/redoc" if settings.effective_api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.effective_api_docs_enabled else None,
)
app.add_middleware(PublicChatBodyLimitMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.effective_allowed_hosts,
)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=not settings.is_local_environment,
)

app.add_exception_handler(AppError, app_error_handler)


logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Phase 6.15.7 — fail closed on unhandled server errors.

    Production responses carry ONLY the stable ``{"error": ...}`` envelope
    with a generic message. The traceback, exception class name, SQL text,
    file paths, and any other internal detail are logged server-side (with
    the request path for correlation) and never returned to the client.
    """
    logger.exception("Unhandled server error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normalize request validation failures to the ``{"error": ...}`` contract.

    Phase 6.13.2 organization registration (and all other schema-validated
    endpoints) must return ``error.code == "VALIDATION_ERROR"`` with HTTP 422
    for missing/invalid/extra fields, matching the project's AppError shape.

    The pydantic error list is sanitized: raw ``errors()`` entries can carry
    non-JSON-serializable ``ctx`` values (e.g. the raised ``ValueError``
    instances from custom field validators), so only the stable ``loc`` /
    ``msg`` / ``type`` triple is returned.
    """
    safe_errors = [
        {
            "loc": list(err.get("loc", ())),
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": safe_errors,
            }
        },
    )


app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(student_auth_router, prefix="/api/v1")
app.include_router(registration_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(institutions_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(student_notifications_router, prefix="/api/v1")
app.include_router(dev_auth_router, prefix="/api/v1")  # DEVELOPMENT / TESTING ONLY

generation_router = APIRouter(prefix="/generation", tags=["generation"])


@generation_router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Process one chat request with persistent conversation and message records.

    Tenant isolation: the client-supplied ``institution_id`` is validated
    against the authenticated user's tenant (resolved server-side from their
    students profile). A student of College A can never retrieve College B's
    knowledge — a mismatch is rejected with 403 TENANT_MISMATCH.
    """
    tenant_id = scope_tenant(current_user, request.institution_id)
    request = request.model_copy(update={"institution_id": tenant_id})
    session_context = resolve_session_context(
        SessionContextRequest(session_id=request.session_id)
    )
    return process_chat_request(
        request,
        session_context,
        OpenRouterGenerationProvider(),
        user_id=current_user["user_id"],
        current_user=current_user,
    )

app.include_router(generation_router, prefix="/api/v1")

# ============================================================================
# Phase 6.13.8 — Public (unauthenticated) AI
# ============================================================================
# Public AI answers ONLY from the public knowledge of the institution selected
# in the request (validated server-side by the public tenant resolver).
# No authentication dependency is attached by design.

public_chat_router = APIRouter(prefix="/chat", tags=["chat"])


@public_chat_router.post(
    "/public",
    response_model=PublicChatResponse,
    summary="Ask a public institution-knowledge question",
    description=(
        "Authentication: Not required. Resolves the public institution code "
        "server-side, retrieves only policy-authorized public knowledge, and "
        "returns a stateless response without internal identifiers or diagnostics."
    ),
    responses={
        400: {
            "model": PublicAPIErrorResponse,
            "description": "The public request is malformed.",
        },
        401: {
            "model": PublicAPIErrorResponse,
            "description": "The question requires authenticated personal data.",
        },
        403: {
            "model": PublicAPIErrorResponse,
            "description": "The institution is not eligible for public chat.",
        },
        404: {
            "model": PublicAPIErrorResponse,
            "description": "The public institution code is unavailable.",
        },
        422: {
            "model": PublicAPIErrorResponse,
            "description": "The request body failed strict validation.",
        },
        413: {
            "model": PublicAPIErrorResponse,
            "description": "The public request body is too large.",
        },
        408: {
            "model": PublicAPIErrorResponse,
            "description": "The public request timed out before completion.",
        },
        429: {
            "model": PublicAPIErrorResponse,
            "description": "The public request rate limit was exceeded.",
        },
        500: {
            "model": PublicAPIErrorResponse,
            "description": "A safe public service error.",
        },
        502: {
            "model": PublicAPIErrorResponse,
            "description": "The generation response was invalid.",
        },
        503: {
            "model": PublicAPIErrorResponse,
            "description": "Public generation is temporarily unavailable.",
        },
        504: {
            "model": PublicAPIErrorResponse,
            "description": "Public generation exceeded the server timeout.",
        },
    },
)
def public_chat(request: PublicChatRequest, http_request: Request) -> PublicChatResponse:
    """Process one PUBLIC (unauthenticated) chat request.

    Phase 7.3:
      * no authentication dependency — public AI requires no login;
      * the public institution code is resolved and validated server-side;
      * the strict request model exposes no retrieval identifiers or controls;
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
    except Exception:
        status = 500
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


@app.get("/")
def root():
    """Friendly landing response for the API root.

    Browsing the backend root previously returned a bare ``{"detail":"Not
    Found"}``, which looks like a broken service. The API itself is fine —
    the real UI is the frontend dev server (http://localhost:5173), which
    proxies ``/api`` to this backend.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "message": "Backend API is running.",
        "health": "/health",
        "readiness": "/ready",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/ready")
def readiness_check():
    """Run a bounded read-only check of the public chat's database dependency."""
    try:
        (
            get_admin_client()
            .table("institutions")
            .select("institution_id")
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("event=readiness_failed dependency=database")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "service": settings.app_name},
        )
    return {"status": "ready", "service": settings.app_name}


@app.get("/api/v1/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """Phase 6.15.4 — canonical authenticated identity + role bootstrap.

    The role and tenant are resolved SERVER-SIDE from the authenticated
    JWT -> public.users -> user_roles -> roles chain (never from any
    client-supplied value). Existing Phase 5.4 response fields are preserved
    byte-for-byte; ``role`` (canonical, single) and ``institution_id`` (tenant
    context, None for platform-level accounts) are additive.

    An account whose active roles contain no supported role resolves to
    ``role: None`` — the frontend treats that as "no privileged UI".
    """
    return {
        "authenticated": True,
        "user_id": current_user["user_id"],
        "auth_user_id": current_user["auth_user_id"],
        "email": current_user["email"],
        "role": resolve_primary_role(current_user.get("roles")),
        "institution_id": current_user.get("institution_id"),
    }


@app.get("/api/v1/dev/auth/status")
def dev_auth_status():
    """DEVELOPMENT / TESTING ONLY.

    Public, unauthenticated flag so the frontend can decide whether to show
    the dev-only password recovery UI. Reveals nothing beyond a boolean and
    is a no-op outside development/testing (always False by default).
    """
    return {"dev_test_mode": settings.dev_test_mode}


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
