"""
Prometheus metrics endpoint and middleware for the QUANTARA API.

Exposes /metrics with:
- http_requests_total: counter by method, endpoint, status
- http_request_duration_seconds: histogram of request latency
- http_requests_in_flight: gauge of concurrent requests
"""

import time

from fastapi import APIRouter
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

router = APIRouter()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP request count",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Number of HTTP requests currently being processed",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that records request count, latency, and in-flight gauge."""

    async def dispatch(self, request: Request, call_next) -> Response:
        endpoint = request.url.path
        method = request.method
        REQUESTS_IN_FLIGHT.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
            REQUESTS_IN_FLIGHT.dec()
        return response


@router.get("/metrics", tags=["Observability"], summary="Prometheus metrics endpoint")
async def metrics() -> Response:
    """Expose Prometheus metrics in text format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
