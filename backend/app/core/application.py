"""Application middleware, configuration validation, and safe HTTP errors."""
import logging
from typing import cast
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.errors import AppError, app_error_handler
from app.core.startup_validation import run_startup_configuration_validation
from app.middleware.public_body_limit import PublicChatBodyLimitMiddleware
from app.middleware.request_limits import RequestSizeLimitMiddleware
from app.middleware.api_rate_limit import ApiRateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


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



def create_application(settings):
    run_startup_configuration_validation(settings)
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.effective_api_docs_enabled else None,
        redoc_url="/redoc" if settings.effective_api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.effective_api_docs_enabled else None,
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=not settings.is_local_environment,
    )
    if settings.effective_cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.effective_cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept"],
            expose_headers=["Retry-After"],
            max_age=600,
        )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.effective_allowed_hosts,
    )
    app.add_middleware(ApiRateLimitMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(PublicChatBodyLimitMiddleware)

    app.add_exception_handler(AppError, cast(ExceptionHandler, app_error_handler))
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    return app
0