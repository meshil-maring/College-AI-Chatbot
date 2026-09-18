import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user, scope_tenant
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
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.session import SessionContextRequest
from app.services.chat import process_chat_request
from app.services.generation_provider import OpenRouterGenerationProvider
from app.services.session import resolve_session_context


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_exception_handler(AppError, app_error_handler)


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
        "environment": settings.environment,
        "message": "Backend is running. This is an API — use the frontend UI at "
        "http://localhost:5173 or the interactive docs below.",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/api/v1/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user_id": current_user["user_id"],
        "auth_user_id": current_user["auth_user_id"],
        "email": current_user["email"],
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
    print(f"Backend (UI entry point):  http://localhost:5173  (frontend dev server)")
    print(f"API root:                  http://127.0.0.1:{port}/")
    print(f"API docs (Swagger UI):     http://127.0.0.1:{port}/docs")
    print(f"Health check:              http://127.0.0.1:{port}/health")
    print(f"Note: {host}:{port} is the bind address and is NOT browsable.\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
