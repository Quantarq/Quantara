import json

class MaxBodySizeMiddleware:
    """ASGI middleware to enforce a maximum request body size.

    Returns a 413 Payload Too Large response if the client request body exceeds
    the configured maximum size (default 1MB).
    """

    def __init__(self, app, max_body_size: int = 1024 * 1024):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check content-length header if present
        content_length = 0
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    pass
                break

        if content_length > self.max_body_size:
            await self._send_413(send)
            return

        # Wrap receive to dynamically count body bytes read
        total_received = 0
        response_sent = False

        async def custom_receive():
            nonlocal total_received, response_sent
            message = await receive()
            if message["type"] == "http.request":
                body_chunk = message.get("body", b"")
                total_received += len(body_chunk)
                if total_received > self.max_body_size:
                    if not response_sent:
                        await self._send_413(send)
                        response_sent = True
                    return {"type": "http.disconnect"}
            return message

        try:
            await self.app(scope, custom_receive, send)
        except Exception:
            if response_sent:
                return
            raise

    async def _send_413(self, send):
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
            ]
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps({"detail": "Request payload too large"}).encode("utf-8"),
            "more_body": False
        })
