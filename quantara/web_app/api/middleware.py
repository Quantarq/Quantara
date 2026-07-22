import json
import os


class SecurityHeadersMiddleware:
    """ASGI middleware that injects security headers into every HTTP response.

    Adds Content-Security-Policy, Strict-Transport-Security (production only),
    X-Frame-Options, X-Content-Type-Options, and Referrer-Policy headers as a
    defense-in-depth measure against XSS, clickjacking, MIME-sniffing, and
    protocol-downgrade attacks.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_production = os.getenv("ENV_VERSION") == "PROD"

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = [
                    (b"content-security-policy", b"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://*.stellar.org; frame-ancestors 'none';"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                if is_production:
                    headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))

                existing_headers = list(message.get("headers", []))
                existing_names = {name.lower() for name, _ in existing_headers}
                filtered = [h for h in existing_headers if h[0].lower() not in {name.lower() for name, _ in headers}]
                message["headers"] = filtered + headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


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


# Paths that accept mutation bodies and must be JSON-only (issue #205).
DEFAULT_MUTATING_PATH_PREFIXES = (
    "/api/add-extra-deposit/",
    "/api/save-bug-report",
)

# Methods that carry a body and should be constrained on mutating routes.
_MUTATING_METHODS = frozenset({b"POST", b"PUT", b"PATCH", b"DELETE"})


class RequireJsonContentTypeMiddleware:
    """Reject non-JSON bodies on mutating API routes.

    FastAPI/Pydantic can accept form-encoded or multipart bodies for models
    that look like JSON. This middleware fails closed on configured mutating
    path prefixes unless ``Content-Type`` is ``application/json`` (optionally
    with a charset parameter). Safe methods (GET/HEAD/OPTIONS) and non-matching
    paths are never blocked.
    """

    def __init__(
        self,
        app,
        mutating_path_prefixes: tuple[str, ...] = DEFAULT_MUTATING_PATH_PREFIXES,
    ):
        self.app = app
        self.mutating_path_prefixes = mutating_path_prefixes

    def _is_mutating_path(self, path: str) -> bool:
        for prefix in self.mutating_path_prefixes:
            if path == prefix.rstrip("/") or path.startswith(prefix):
                return True
        return False

    @staticmethod
    def _content_type(scope) -> str:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-type":
                return value.decode("latin-1").split(";", 1)[0].strip().lower()
        return ""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").encode("ascii")
        path = scope.get("path", "")
        is_mutating = self._is_mutating_path(path)

        # Expose flag for downstream consumers as noted in #205.
        state = scope.get("state")
        if state is not None and not isinstance(state, dict):
            try:
                state.is_mutating = is_mutating
            except Exception:
                pass
        else:
            scope.setdefault("state", {})
            if isinstance(scope["state"], dict):
                scope["state"]["is_mutating"] = is_mutating

        if method in _MUTATING_METHODS and is_mutating:
            content_type = self._content_type(scope)
            if content_type != "application/json":
                await self._send_415(send)
                return

        await self.app(scope, receive, send)

    async def _send_415(self, send):
        body = json.dumps(
            {
                "detail": "Unsupported Media Type. Use Content-Type: application/json",
                "accept": "application/json",
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 415,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"accept", b"application/json"),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )
