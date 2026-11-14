import json
import logging
import time
from uuid import uuid4

from starlette.requests import Request

from app.core.errors import APIError, error_response
from app.core.request_cache import request_cache

logger = logging.getLogger("learning_api.requests")


class RequestBoundary:
    """Bound bodies before JSON parsing; log route templates, never tokens or bodies."""

    def __init__(self, app, *, max_body_bytes: int, production: bool):
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.production = production

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.monotonic()
        status = 500

        async def guarded_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"x-request-id", b"cache-control"}
                ]
                message.setdefault("headers", []).extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
                if self.production:
                    message["headers"].append((b"strict-transport-security", b"max-age=31536000"))
            await send(message)

        async def reject(status_code, code, message):
            response = error_response(Request(scope), APIError(status_code, code, message))
            await response(scope, receive, guarded_send)

        if self.production and scope.get("scheme") != "https":
            await reject(400, "HTTPS_REQUIRED", "Use HTTPS")
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await reject(413, "BODY_TOO_LARGE", "Request body exceeds the configured limit")
                return
            if not message.get("more_body", False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        token = request_cache.set({})
        try:
            await self.app(scope, replay, guarded_send)
        finally:
            request_cache.reset(token)
            route = scope.get("route")
            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "method": scope["method"],
                        "route": getattr(route, "path", "unmatched"),
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000),
                    }
                )
            )
