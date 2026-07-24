"""
Standardised error envelope and custom OpenAPI schema generator.

Every error response from the Quantara API uses the same JSON shape::

    {
        "detail": "Human-readable description of what went wrong.",
        "code":   "machine_readable_error_code",
        "request_id": "uuid-attached-to-this-request"
    }

Usage
-----
Raise :class:`APIError` instead of FastAPI's bare ``HTTPException``:

    from web_app.api.errors import APIError
    raise APIError(status_code=status.HTTP_404_NOT_FOUND, code="position_not_found",
                   detail="No position with that ID exists.")

The ``request_id`` is injected automatically from the structlog context set by
the ``request_id_middleware`` in ``main.py``.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Error envelope schema
# ---------------------------------------------------------------------------


class ErrorEnvelope(BaseModel):
    """Standardised JSON error response body."""

    detail: str = Field(
        ...,
        description="Human-readable description of what went wrong.",
        example="No position with that ID exists.",
    )
    code: str = Field(
        ...,
        description="Machine-readable error code for client-side handling.",
        example="position_not_found",
    )
    request_id: str = Field(
        ...,
        description="Unique identifier for this request (echo of X-Request-Id header).",
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "No position with that ID exists.",
                "code": "position_not_found",
                "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            }
        }
    }


# ---------------------------------------------------------------------------
# APIError — typed HTTPException with a machine-readable code
# ---------------------------------------------------------------------------


class APIError(HTTPException):
    """
    HTTPException subclass that carries a machine-readable ``code``.

    Parameters
    ----------
    status_code:
        HTTP status code (e.g. 400, 404, 422).
    code:
        Snake-case error identifier (e.g. ``"position_not_found"``).
    detail:
        Human-readable explanation shown to the caller.
    headers:
        Optional extra response headers.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        headers: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Convert an :class:`APIError` into a standard :class:`ErrorEnvelope` response.

    Registered via ``app.add_exception_handler(APIError, api_error_handler)``
    in ``main.py``.
    """
    request_id: str = (
        structlog.contextvars.get_contextvars().get("request_id")
        or request.headers.get("X-Request-Id", "-")
    )
    body = ErrorEnvelope(
        detail=exc.detail,
        code=exc.code,
        request_id=request_id,
    )
    headers = dict(exc.headers or {})
    headers["X-Request-Id"] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Shared 4xx / 5xx response specs injected into every endpoint by the
# custom OpenAPI generator.
# ---------------------------------------------------------------------------

COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Bad Request — invalid input or missing required field.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "detail": "multiplier must be a valid number",
                    "code": "validation_error",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                },
            }
        },
    },
    401: {
        "description": "Unauthorized — authentication is required.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "detail": "Wallet signature verification failed.",
                    "code": "unauthorized",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                },
            }
        },
    },
    404: {
        "description": "Not Found — the requested resource does not exist.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "detail": "No position with that ID exists.",
                    "code": "not_found",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                },
            }
        },
    },
    422: {
        "description": "Unprocessable Entity — request body failed schema validation.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "detail": "field required: wallet_id",
                    "code": "unprocessable_entity",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                },
            }
        },
    },
    500: {
        "description": "Internal Server Error.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "detail": "Internal server error",
                    "code": "internal_server_error",
                    "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                },
            }
        },
    },
}
