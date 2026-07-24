from web_app.api.main import app
from starlette.middleware.gzip import GZipMiddleware


def test_gzip_middleware_registered_for_json_payloads_over_1kb():
    middleware_classes = [m.cls for m in app.user_middleware]
    assert GZipMiddleware in middleware_classes

    gzip_entry = next(m for m in app.user_middleware if m.cls is GZipMiddleware)
    assert gzip_entry.kwargs["minimum_size"] == 1024
