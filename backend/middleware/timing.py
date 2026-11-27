
"""Request processing time middleware."""

from time import perf_counter
from typing import Any


class RequestTimingMiddleware:
    """Measure HTTP request processing time."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = perf_counter()

        async def send_with_timing(message):
            if message["type"] == "http.response.start":
                duration = perf_counter() - start_time
                duration_ms = duration * 1000

                headers = list(message.get("headers", []))
                headers.append(
                    (
                        b"x-process-time-ms",
                        f"{duration_ms:.2f}".encode("ascii"),
                    )
                )
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_timing)
