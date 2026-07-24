import asyncio
import unittest

from starlette.responses import JSONResponse

from Security.middleware import RequestBodyLimitMiddleware


class RequestBodyLimitMiddlewareTests(unittest.TestCase):
    def test_rejects_chunked_body_without_content_length(self) -> None:
        received_messages = iter(
            [
                {"type": "http.request", "body": b"1234", "more_body": True},
                {"type": "http.request", "body": b"5678", "more_body": False},
            ]
        )
        sent_messages = []

        async def receive():
            return next(received_messages)

        async def send(message):
            sent_messages.append(message)

        async def consume_body_app(scope, receive, send):
            while True:
                message = await receive()
                if not message.get("more_body", False):
                    break

            response = JSONResponse({"status": "unexpected"})
            await response(scope, receive, send)

        middleware = RequestBodyLimitMiddleware(
            consume_body_app,
            max_body_bytes=6,
        )
        scope = {
            "type": "http",
            "method": "POST",
            "headers": [(b"transfer-encoding", b"chunked")],
        }

        asyncio.run(middleware(scope, receive, send))

        self.assertEqual(sent_messages[0]["type"], "http.response.start")
        self.assertEqual(sent_messages[0]["status"], 413)


if __name__ == "__main__":
    unittest.main()
