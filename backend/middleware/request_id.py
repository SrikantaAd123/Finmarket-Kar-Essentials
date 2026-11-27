
"""Request ID middleware."""

from uuid import uuid4
from typing import Any


class RequestIDMiddleware:
    """Attach a unique request ID to every HTTP request."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", request_id.encode("ascii"))
                )
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_request_id)
