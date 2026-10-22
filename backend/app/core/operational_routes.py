"""Operational API endpoints with bounded read-only readiness checks."""
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_operational_routes(app, settings, database) -> None:
    router = APIRouter()

    @router.get("/")
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


    @router.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.environment,
        }


    @router.get("/ready")
    def readiness_check():
        """Run a bounded read-only check of the public chat's database dependency."""
        try:
            (
                database()
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


    app.include_router(router)
