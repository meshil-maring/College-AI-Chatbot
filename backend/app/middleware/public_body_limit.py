"""Early HTTP body cap scoped only to the public chat route."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import settings


class PublicChatBodyLimitMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict,
        receive: Callable[[], Awaitable[dict]],
        send,
    ) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/v1/chat/public"
        ):
            await self.app(scope, receive, send)
            return

        limit = settings.public_max_body_bytes
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                if int(raw_length) > limit:
                    await self._reject(
                        send,
                        413,
                        "PUBLIC_REQUEST_TOO_LARGE",
                        "The public chat request is too large.",
                    )
                    return
            except ValueError:
                await self._reject(
                    send,
                    400,
                    "PUBLIC_REQUEST_INVALID",
                    "The public chat request is malformed.",
                )
                return

        body = bytearray()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.public_body_read_timeout_seconds
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                await self._reject(
                    send,
                    408,
                    "PUBLIC_REQUEST_TIMEOUT",
                    "The public chat request timed out.",
                )
                return
            try:
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except TimeoutError:
                await self._reject(
                    send,
                    408,
                    "PUBLIC_REQUEST_TIMEOUT",
                    "The public chat request timed out.",
                )
                return
            if message.get("type") == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                await self._reject(
                    send,
                    413,
                    "PUBLIC_REQUEST_TOO_LARGE",
                    "The public chat request is too large.",
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

    @staticmethod
    async def _reject(send, status: int, code: str, message: str) -> None:
        payload = json.dumps(
            {
                "error": {
                    "code": code,
                    "message": message,
                }
            }
        ).encode("utf-8")
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
