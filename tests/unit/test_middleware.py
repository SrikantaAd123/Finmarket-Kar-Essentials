
"""Unit tests for custom ASGI middleware."""

import asyncio

from backend.middleware import (
    RequestIDMiddleware,
    RequestTimingMiddleware,
    SecurityHeadersMiddleware,
)


def run_asgi_middleware(middleware_class):
    """Run middleware with a small in-memory ASGI application."""

    captured = []
    request_scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "state": {},
    }

    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({
            "type": "http.response.body",
            "body": b"OK",
            "more_body": False,
        })

    async def receive():
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }

    async def send(message):
        captured.append(message)

    middleware = middleware_class(app)

    asyncio.run(
        middleware(request_scope, receive, send)
    )

    return request_scope, captured


def test_request_id_middleware_adds_header():
    scope, messages = run_asgi_middleware(RequestIDMiddleware)

    response = messages[0]
    headers = dict(response["headers"])

    assert b"x-request-id" in headers
    assert scope["state"]["request_id"] == (
        headers[b"x-request-id"].decode()
    )


def test_request_id_middleware_generates_unique_ids():
    _, first_messages = run_asgi_middleware(RequestIDMiddleware)
    _, second_messages = run_asgi_middleware(RequestIDMiddleware)

    first_id = dict(first_messages[0]["headers"])[b"x-request-id"]
    second_id = dict(second_messages[0]["headers"])[b"x-request-id"]

    assert first_id != second_id


def test_timing_middleware_adds_duration_header():
    _, messages = run_asgi_middleware(RequestTimingMiddleware)

    headers = dict(messages[0]["headers"])

    assert b"x-process-time-ms" in headers
    assert float(headers[b"x-process-time-ms"]) >= 0


def test_security_headers_middleware():
    _, messages = run_asgi_middleware(SecurityHeadersMiddleware)

    headers = dict(messages[0]["headers"])

    assert headers[b"x-content-type-options"] == b"nosniff"
    assert headers[b"x-frame-options"] == b"DENY"
    assert (
        headers[b"referrer-policy"]
        == b"strict-origin-when-cross-origin"
    )
    assert b"permissions-policy" in headers


def test_security_middleware_preserves_existing_header():
    captured = []

    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"x-frame-options", b"SAMEORIGIN"),
            ],
        })

    async def receive():
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }

    async def send(message):
        captured.append(message)

    middleware = SecurityHeadersMiddleware(app)

    asyncio.run(
        middleware(
            {"type": "http", "state": {}},
            receive,
            send,
        )
    )

    headers = dict(captured[0]["headers"])

    assert headers[b"x-frame-options"] == b"SAMEORIGIN"
