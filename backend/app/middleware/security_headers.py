from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Attach conservative API-safe response headers.

    The frontend's CSP belongs at its static hosting layer. HSTS is emitted
    only for deployed environments, where TLS must terminate at the platform
    or reverse proxy.
    """

    def __init__(self, app: ASGIApp, *, enable_hsts: bool) -> None:
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}

                def add(name: bytes, value: bytes) -> None:
                    if name.lower() not in existing:
                        headers.append((name, value))
                        existing.add(name.lower())

                add(b"x-content-type-options", b"nosniff")
                add(b"referrer-policy", b"no-referrer")
                add(b"x-frame-options", b"DENY")
                add(b"x-permitted-cross-domain-policies", b"none")
                add(
                    b"permissions-policy",
                    b"camera=(), microphone=(), geolocation=()",
                )
                path = str(scope.get("path") or "")
                if path.startswith("/api/"):
                    add(b"cache-control", b"no-store")
                if self.enable_hsts:
                    add(
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains",
                    )
                    # The deployed backend is an API, not an HTML application.
                    # Swagger/ReDoc are disabled in this environment, so a
                    # deny-all document policy is safe and prevents accidental
                    # active content execution if an error is served as HTML.
                    add(
                        b"content-security-policy",
                        b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
