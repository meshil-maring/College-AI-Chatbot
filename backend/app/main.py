import uvicorn
from fastapi import APIRouter, Depends, FastAPI

from app.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.api.ingestion import router as ingestion_router
from app.api.auth import router as auth_router
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
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

generation_router = APIRouter(prefix="/generation", tags=["generation"])


@generation_router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Process one chat request with persistent conversation and message records."""
    session_context = resolve_session_context(
        SessionContextRequest(session_id=request.session_id)
    )
    return process_chat_request(
        request,
        session_context,
        OpenRouterGenerationProvider(),
        user_id=current_user["user_id"],
    )


app.include_router(generation_router, prefix="/api/v1")


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


def start():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
