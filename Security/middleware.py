from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLargeError(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await self._send_error(scope, receive, send, 400, "Invalid Content-Length.")
                return

            if declared_size < 0:
                await self._send_error(scope, receive, send, 400, "Invalid Content-Length.")
                return

            if declared_size > self.max_body_bytes:
                await self._send_too_large(scope, receive, send)
                return

        received_size = 0

        async def limited_receive() -> Message:
            nonlocal received_size
            message = await receive()

            if message["type"] == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_body_bytes:
                    raise RequestBodyTooLargeError

            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLargeError:
            await self._send_too_large(scope, receive, send)

    async def _send_too_large(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await self._send_error(
            scope,
            receive,
            send,
            413,
            "Request body is too large.",
        )

    @staticmethod
    async def _send_error(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
    ) -> None:
        response = JSONResponse({"detail": detail}, status_code=status_code)
        await response(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, include_hsts: bool = False) -> None:
        self.app = app
        self.include_hsts = include_hsts

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("Cache-Control", "no-store")
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), geolocation=(), microphone=()",
                )
                if self.include_hsts:
                    headers.setdefault(
                        "Strict-Transport-Security",
                        "max-age=31536000; includeSubDomains",
                    )

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
