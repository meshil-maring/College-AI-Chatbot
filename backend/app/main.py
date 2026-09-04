import uvicorn
from fastapi import FastAPI, Depends

from app.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.api.ingestion import router as ingestion_router
from app.api.auth import router as auth_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_exception_handler(AppError, app_error_handler)
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


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
