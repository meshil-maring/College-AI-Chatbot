"""Route-aware request-size enforcement before request parsing.

JSON/webhook bodies are buffered only up to their small configured cap and are
then replayed to FastAPI. Multipart uploads must declare Content-Length and are
stream-counted while Starlette parses them, preventing chunked/body-length
bypasses without retaining the whole upload in application memory.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import settings


class _RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    _BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    _UPLOAD_PATHS = frozenset(
        {
            "/api/v1/documents/ingest",
            "/api/v1/admin/documents",
            "/api/v1/admin/results/csv-upload",
        }
    )

    def __init__(self, app: Any) -> None:
        self.app = app

    @classmethod
    def _is_upload_path(cls, path: str) -> bool:
        return path in cls._UPLOAD_PATHS or (
            path.startswith("/api/v1/admin/documents/")
            and path.endswith("/versions")
        )

    @staticmethod
    def _limit_for(path: str) -> int:
        if path == "/api/v1/webhooks/mailgun":
            return settings.webhook_max_body_bytes
        if RequestSizeLimitMiddleware._is_upload_path(path):
            return settings.max_upload_request_body_bytes
        return settings.max_request_body_bytes

    async def __call__(
        self,
        scope: dict,
        receive: Callable[[], Awaitable[dict]],
        send,
    ) -> None:
        method = str(scope.get("method") or "").upper()
        path = str(scope.get("path") or "")
        if (
            scope.get("type") != "http"
            or method not in self._BODY_METHODS
            or not path.startswith("/api/")
            or path == "/api/v1/chat/public"  # tighter legacy boundary
        ):
            await self.app(scope, receive, send)
            return

        limit = self._limit_for(path)
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        declared_length: int | None = None
        if raw_length is not None:
            try:
                declared_length = int(raw_length)
                if declared_length < 0:
                    raise ValueError
            except ValueError:
                await self._reject(send, 400, "REQUEST_INVALID", "The request is malformed.")
                return
            if declared_length > limit:
                code = "FILE_TOO_LARGE" if self._is_upload_path(path) else "REQUEST_TOO_LARGE"
                await self._reject(
                    send,
                    413,
                    code,
                    "The request body is too large.",
                )
                return

        is_upload = self._is_upload_path(path)
        if is_upload and declared_length is None:
            await self._reject(
                send,
                411,
                "CONTENT_LENGTH_REQUIRED",
                "Content-Length is required for file uploads.",
            )
            return

        # Small non-upload payloads are bounded and timed before parsing. This
        # also protects against chunked transfer and slow-body attacks.
        if not is_upload:
            body = bytearray()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + settings.request_body_read_timeout_seconds
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    await self._reject(send, 408, "REQUEST_TIMEOUT", "The request timed out.")
                    return
                try:
                    message = await asyncio.wait_for(receive(), timeout=remaining)
                except TimeoutError:
                    await self._reject(send, 408, "REQUEST_TIMEOUT", "The request timed out.")
                    return
                if message.get("type") == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > limit:
                    await self._reject(
                        send, 413, "REQUEST_TOO_LARGE", "The request body is too large."
                    )
                    return
                if not message.get("more_body", False):
                    break

            delivered = False

            async def replay() -> dict:
                nonlocal delivered
                if delivered:
                    return {"type": "http.request", "body": b"", "more_body": False}
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            await self.app(scope, replay, send)
            return

        # Multipart bodies are already declared below the cap. Count actual
        # bytes too, so a dishonest Content-Length cannot bypass the limit.
        consumed = 0

        async def limited_receive() -> dict:
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > limit:
                raise _RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLarge:
            code = "FILE_TOO_LARGE" if is_upload else "REQUEST_TOO_LARGE"
            await self._reject(
                send, 413, code, "The request body is too large."
            )

    @staticmethod
    async def _reject(send, status: int, code: str, message: str) -> None:
        payload = json.dumps({"error": {"code": code, "message": message}}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
