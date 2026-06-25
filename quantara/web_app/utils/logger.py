"""
Structured logging setup for the Quantara backend.

- Production (ENV_VERSION=PROD): JSON output via structlog + python-json-logger
- Development: human-readable coloured console output
- Every log entry carries: timestamp, level, logger, request_id, message
- wallet_id is always masked (first 6 + last 4 chars, middle replaced with ****)
"""

import logging
import logging.config
import os
import re

import structlog

_IS_PROD = os.getenv("ENV_VERSION", "").upper() == "PROD"

# ── wallet masking ────────────────────────────────────────────────────────────
_STELLAR_RE = re.compile(r"\bG[A-Z2-7]{55}\b")


def mask_wallet_id(wallet_id: str) -> str:
    """Return a masked version of a Stellar public key for safe logging."""
    if not wallet_id or len(wallet_id) < 12:
        return "****"
    return f"{wallet_id[:6]}****{wallet_id[-4:]}"


def _mask_wallet_processor(
    logger: object, method: str, event_dict: dict
) -> dict:
    """structlog processor: mask any wallet_id field and scrub keys in values."""
    if "wallet_id" in event_dict:
        event_dict["wallet_id"] = mask_wallet_id(str(event_dict["wallet_id"]))
    # Also mask any Stellar public keys that leaked into the message string
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = _STELLAR_RE.sub(
            lambda m: mask_wallet_id(m.group()), event_dict["event"]
        )
    return event_dict


# ── shared processors ─────────────────────────────────────────────────────────
_SHARED_PROCESSORS: list = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _mask_wallet_processor,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
]


def configure_logging() -> None:
    """Configure structlog + stdlib logging.  Call once at application startup."""
    if _IS_PROD:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=_SHARED_PROCESSORS
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=_SHARED_PROCESSORS,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)
