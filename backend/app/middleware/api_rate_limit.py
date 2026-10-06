"""Coarse application-wide and authenticated-AI request budgets."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.config import settings
from app.services.public_abuse_controls import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)
api_rate_limiter = SlidingWindowRateLimiter()


class ApiRateLimitMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive, send) -> None:
        path = str(scope.get("path") or "")
        if (
            scope.get("type") != "http"
            or not path.startswith("/api/")
            or not settings.api_rate_limit_enabled
        ):
            await self.app(scope, receive, send)
            return

        peer = scope.get("client")
        client_identity = str(peer[0]) if peer else "unknown"
        rules = [
            ("api-client", client_identity, settings.api_client_rate_limit_requests),
            ("api-global", "all", settings.api_global_rate_limit_requests),
        ]
        if path == "/api/v1/generation/chat":
            headers = {key.lower(): value for key, value in scope.get("headers", [])}
            authorization = headers.get(b"authorization", b"")
            # Hashing avoids retaining a usable credential in limiter state.
            credential = hashlib.sha256(authorization).hexdigest() if authorization else client_identity
            rules.append(
                (
                    "authenticated-ai",
                    credential,
                    settings.authenticated_ai_rate_limit_requests,
                )
            )

        retry_after = api_rate_limiter.check(rules, settings.api_rate_limit_window_seconds)
        if retry_after is not None:
            logger.warning("event=api_rate_limited path=%s status=429", path)
            await self._reject(send, retry_after)
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send, retry_after: int) -> None:
        payload = json.dumps(
            {
                "error": {
                    "code": "API_RATE_LIMITED",
                    "message": "Too many requests. Please try again later.",
                }
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                    (b"retry-after", str(retry_after).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})


def reset_api_rate_limit_state() -> None:
    api_rate_limiter.reset()
