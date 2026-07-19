"""
Admin pause controls and request guard for incident response.
"""

import os
from dataclasses import dataclass
from threading import Lock

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse


PROTOCOL_PAUSED_DETAIL = "Protocol paused"
ADMIN_PAUSE_PREFIX = "/api/admin/pause"
PAUSE_ADMIN_TOKEN_ENV = "PAUSE_ADMIN_TOKEN"


@dataclass(frozen=True)
class PauseStatus:
    paused: bool


class PauseController:
    """Thread-safe in-process protocol pause switch."""

    def __init__(self) -> None:
        self._paused = False
        self._lock = Lock()

    def pause(self) -> PauseStatus:
        with self._lock:
            self._paused = True
            return PauseStatus(paused=self._paused)

    def unpause(self) -> PauseStatus:
        with self._lock:
            self._paused = False
            return PauseStatus(paused=self._paused)

    def status(self) -> PauseStatus:
        with self._lock:
            return PauseStatus(paused=self._paused)


pause_controller = PauseController()
router = APIRouter(prefix=ADMIN_PAUSE_PREFIX, tags=["Admin"])


def _admin_token() -> str | None:
    return os.getenv(PAUSE_ADMIN_TOKEN_ENV) or os.getenv("ADMIN_API_KEY")


def verify_admin_token(x_admin_token: str = Header(...)) -> None:
    expected_token = _admin_token()
    if not expected_token or x_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="Admin authorization required")


def is_pause_exempt_path(path: str) -> bool:
    return (
        path.startswith(ADMIN_PAUSE_PREFIX)
        or path == "/health"
        or path.startswith("/metrics")
    )


async def protocol_pause_middleware(request: Request, call_next):
    if (
        request.url.path.startswith("/api/")
        and not is_pause_exempt_path(request.url.path)
        and pause_controller.status().paused
    ):
        return JSONResponse(status_code=503, content={"detail": PROTOCOL_PAUSED_DETAIL})

    return await call_next(request)


@router.get("", summary="Get protocol pause status")
async def get_pause_status(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    return {"paused": pause_controller.status().paused}


@router.post("", summary="Pause protocol user-facing operations")
async def pause_protocol(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    return {"paused": pause_controller.pause().paused}


@router.delete("", summary="Unpause protocol user-facing operations")
async def unpause_protocol(
    x_admin_token: str = Header(..., alias="X-Admin-Token"),
) -> dict:
    verify_admin_token(x_admin_token)
    return {"paused": pause_controller.unpause().paused}
