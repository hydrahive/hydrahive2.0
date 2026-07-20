"""ASGI request-body limit for chat attachment endpoints."""
from __future__ import annotations

import re

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MIB = 1024 * 1024
MAX_CHAT_REQUEST_BYTES = 205 * MIB
_CHAT_MESSAGE_PATH = re.compile(
    r"^/api/sessions/[^/]+/messages(?:/[^/]+/resend)?/?$"
)


class _RequestBodyTooLarge(Exception):
    pass


class ChatUploadLimitMiddleware:
    """Reject oversized chat message bodies before multipart parsing."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_CHAT_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await self._reject(scope, receive, send)

    @staticmethod
    def _applies(scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and bool(_CHAT_MESSAGE_PATH.fullmatch(scope.get("path", "")))
        )

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return None

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "code": "upload_request_too_large",
                    "params": {"max_mib": self.max_bytes // MIB},
                }
            },
        )
        await response(scope, receive, send)
