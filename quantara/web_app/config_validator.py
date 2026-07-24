"""
Configuration validator for the QUANTARA web application.

Validates required environment variables at application startup to
fail fast when critical configuration is missing, rather than
encountering cryptic runtime errors when those values are used.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)
SESSION_SECRET_MIN_LENGTH = 32


@dataclass
class ConfigValidationError:
    """
    Represents a single environment variable validation error.

    :param variable: Name of the environment variable.
    :param message: Human-readable description of the validation failure.
    """

    variable: str
    message: str


@dataclass
class ConfigValidationResult:
    """
    Result of a configuration validation pass.

    :param errors: List of validation errors. Empty when valid.
    """

    errors: List[ConfigValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """
        Return True if no validation errors were found.
        """
        return len(self.errors) == 0

    def format_errors(self) -> str:
        """
        Format all errors as a multi-line human-readable string.
        """
        if not self.errors:
            return ""
        lines = ["Configuration validation failed:"]
        for err in self.errors:
            lines.append(f"  - {err.variable}: {err.message}")
        return "\n".join(lines)


# Required environment variables in production.
# In development, these can fall back to defaults defined in db/database.py.
_REQUIRED_IN_PRODUCTION = (
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_NAME",
    "SESSION_SECRET_KEY",
)

# Optional environment variables with no required value.
_OPTIONAL_BUT_RECOMMENDED = (
    "SENTRY_DSN",
    "STELLAR_HORIZON_URL",
    "STELLAR_SOROBAN_RPC_URL",
)


def _is_production() -> bool:
    """
    Return True if the application is running in production mode.
    """
    return os.getenv("ENV_VERSION") == "PROD"


def validate_required_env_vars(
    is_production: Optional[bool] = None,
) -> ConfigValidationResult:
    """
    Validate that required environment variables are set and well-formed.

    In production, raises errors for any missing required variable.
    In development, only warns about missing optional-but-recommended
    variables, allowing local development with .env defaults.

    :param is_production: Override the production detection. If None,
        the function reads ENV_VERSION from the environment.
    :return: ConfigValidationResult containing any errors found.
    """
    if is_production is None:
        is_production = _is_production()

    result = ConfigValidationResult()

    if is_production:
        for var in _REQUIRED_IN_PRODUCTION:
            value = os.getenv(var)
            if not value:
                result.errors.append(
                    ConfigValidationError(
                        variable=var,
                        message=(
                            "Required environment variable is not set. "
                            "This must be configured before starting the "
                            "application in production."
                        ),
                    )
                )

        session_secret = os.getenv("SESSION_SECRET_KEY")
        if session_secret and len(session_secret) < SESSION_SECRET_MIN_LENGTH:
            result.errors.append(
                ConfigValidationError(
                    variable="SESSION_SECRET_KEY",
                    message=(
                        "SESSION_SECRET_KEY must be at least "
                        f"{SESSION_SECRET_MIN_LENGTH} characters long."
                    ),
                )
            )

        # In production, Sentry DSN is also required for error tracking.
        sentry_dsn = os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            result.errors.append(
                ConfigValidationError(
                    variable="SENTRY_DSN",
                    message=(
                        "Sentry DSN must be set in production for error "
                        "tracking. Configure SENTRY_DSN to enable Sentry."
                    ),
                )
            )
    else:
        # In development, only warn about missing optional variables.
        for var in _OPTIONAL_BUT_RECOMMENDED:
            value = os.getenv(var)
            if not value:
                logger.warning(
                    "Optional environment variable %s is not set. "
                    "This is fine for local development but should be "
                    "configured in production.",
                    var,
                )

    return result


def assert_valid_config(is_production: Optional[bool] = None) -> None:
    """
    Validate the configuration and raise if invalid.

    Logs a clear error message and raises RuntimeError when validation
    fails. Use this at application startup to fail fast when
    configuration is missing or invalid.

    :param is_production: Override the production detection.
    :raises RuntimeError: If configuration validation fails.
    """
    result = validate_required_env_vars(is_production=is_production)
    if not result.is_valid:
        formatted = result.format_errors()
        logger.error(formatted)
        raise RuntimeError(formatted)
