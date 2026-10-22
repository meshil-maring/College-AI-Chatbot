"""Public chat OpenAPI error contracts."""
from app.schemas.ai.chat import PublicAPIErrorResponse

PUBLIC_CHAT_RESPONSES = {
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
            "description": "Public chat or a required dependency is temporarily unavailable.",
        },
        504: {
            "model": PublicAPIErrorResponse,
            "description": "Public generation exceeded the server timeout.",
        },
    }
