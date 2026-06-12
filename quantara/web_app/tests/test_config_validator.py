"""
Tests for the config_validator module.

Verifies that the startup-time environment variable validator:
- Returns no errors when all required vars are set in production
- Returns errors for missing required vars in production
- Does not raise in development mode (only warns)
- Formats errors as a human-readable multi-line string
- assert_valid_config raises RuntimeError on failure
"""

import os
from unittest.mock import patch

import pytest

from web_app.config_validator import (
    ConfigValidationError,
    ConfigValidationResult,
    assert_valid_config,
    validate_required_env_vars,
)


class TestConfigValidationResult:
    def test_is_valid_when_no_errors(self):
        result = ConfigValidationResult()
        assert result.is_valid is True

    def test_is_invalid_when_errors(self):
        result = ConfigValidationResult(
            errors=[ConfigValidationError(variable="FOO", message="bad")]
        )
        assert result.is_valid is False

    def test_format_errors_returns_empty_when_valid(self):
        result = ConfigValidationResult()
        assert result.format_errors() == ""

    def test_format_errors_lists_each_error(self):
        result = ConfigValidationResult(
            errors=[
                ConfigValidationError(variable="FOO", message="bad"),
                ConfigValidationError(variable="BAR", message="missing"),
            ]
        )
        formatted = result.format_errors()
        assert "FOO" in formatted
        assert "bad" in formatted
        assert "BAR" in formatted
        assert "missing" in formatted


class TestValidateRequiredEnvVars:
    def test_returns_valid_in_development_without_required_vars(self):
        # In development mode, no errors should be raised even
        # without any required vars set.
        with patch.dict(
            os.environ,
            {"ENV_VERSION": "DEV"},
            clear=True,
        ):
            result = validate_required_env_vars()
        assert result.is_valid is True

    def test_returns_errors_in_production_without_required_vars(self):
        with patch.dict(os.environ, {"ENV_VERSION": "PROD"}, clear=True):
            result = validate_required_env_vars()
        assert result.is_valid is False
        variables = {err.variable for err in result.errors}
        assert "DB_USER" in variables
        assert "DB_PASSWORD" in variables
        assert "DB_HOST" in variables
        assert "DB_NAME" in variables
        assert "SESSION_SECRET_KEY" in variables
        assert "SENTRY_DSN" in variables

    def test_returns_valid_in_production_with_all_required_vars(self):
        env = {
            "ENV_VERSION": "PROD",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_HOST": "localhost",
            "DB_NAME": "quantara",
            "SESSION_SECRET_KEY": "x" * 32,
            "SENTRY_DSN": "https://example@sentry.io/123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = validate_required_env_vars()
        assert result.is_valid is True

    def test_is_production_override_takes_precedence(self):
        # Explicitly pass is_production=True to validate as production
        # even when ENV_VERSION is unset.
        with patch.dict(os.environ, {}, clear=True):
            result = validate_required_env_vars(is_production=True)
        assert result.is_valid is False
        variables = {err.variable for err in result.errors}
        assert "DB_USER" in variables


class TestAssertValidConfig:
    def test_does_not_raise_in_development(self):
        with patch.dict(os.environ, {"ENV_VERSION": "DEV"}, clear=True):
            # Should not raise
            assert_valid_config()

    def test_raises_runtime_error_in_production_without_required_vars(self):
        with patch.dict(os.environ, {"ENV_VERSION": "PROD"}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                assert_valid_config()
        # The error message should mention the missing variables
        assert "DB_USER" in str(exc_info.value)
        assert "SESSION_SECRET_KEY" in str(exc_info.value)
