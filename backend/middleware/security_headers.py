
"""HTTP security headers middleware."""

from typing import Any


class SecurityHeadersMiddleware:
    """Add security headers to HTTP responses."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (
                        b"referrer-policy",
                        b"strict-origin-when-cross-origin",
                    ),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()",
                    ),
                ]

                existing = {name.lower() for name, _ in headers}

                for name, value in security_headers:
                    if name not in existing:
                        headers.append((name, value))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
