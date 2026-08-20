"""
Tests for the config_validator module.

Verifies that the startup-time environment variable validator:
- Returns no errors when all required vars are set in production
- Returns errors for missing required vars in production
- Does not raise in development mode (only warns)
- Formats errors as a human-readable multi-line string
- assert_valid_config raises RuntimeError on failure
"""

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
    def test_returns_valid_in_development_without_required_vars(self, monkeypatch):
        # In development mode, no errors should be raised even
        # without any required vars set.
        monkeypatch.setenv("ENV_VERSION", "DEV")
        # Remove any pre-existing relevant vars so we test a clean dev env.
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN",
        ):
            monkeypatch.delenv(var, raising=False)
        result = validate_required_env_vars()
        assert result.is_valid is True

    def test_returns_errors_in_production_without_required_vars(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "PROD")
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN",
        ):
            monkeypatch.delenv(var, raising=False)
        result = validate_required_env_vars()
        assert result.is_valid is False
        variables = {err.variable for err in result.errors}
        assert "DB_USER" in variables
        assert "DB_PASSWORD" in variables
        assert "DB_HOST" in variables
        assert "DB_NAME" in variables
        assert "SESSION_SECRET_KEY" in variables
        assert "SENTRY_DSN" in variables

    def test_returns_valid_in_production_with_all_required_vars(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "PROD")
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_NAME", "quantara")
        monkeypatch.setenv("SESSION_SECRET_KEY", "x" * 32)
        monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/123")
        result = validate_required_env_vars()
        assert result.is_valid is True

    def test_is_production_override_takes_precedence(self, monkeypatch):
        # Explicitly pass is_production=True to validate as production
        # even when ENV_VERSION is unset.
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN", "ENV_VERSION",
        ):
            monkeypatch.delenv(var, raising=False)
        result = validate_required_env_vars(is_production=True)
        assert result.is_valid is False
        variables = {err.variable for err in result.errors}
        assert "DB_USER" in variables

    def test_invalid_usdc_issuer_is_rejected_in_development(self, monkeypatch):
        """A malformed USDC issuer must fail fast in every environment."""
        monkeypatch.setenv("ENV_VERSION", "DEV")
        monkeypatch.setenv("USDC_ASSET_ISSUER", "not-a-stellar-key")
        result = validate_required_env_vars()
        variables = {err.variable for err in result.errors}
        assert "USDC_ASSET_ISSUER" in variables

    def test_invalid_usdc_issuer_is_rejected_in_production(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "PROD")
        monkeypatch.setenv("USDC_ASSET_ISSUER", "not-a-stellar-key")
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN",
        ):
            monkeypatch.setenv(var, "x")
        result = validate_required_env_vars()
        variables = {err.variable for err in result.errors}
        assert "USDC_ASSET_ISSUER" in variables

    def test_valid_explicit_usdc_issuer_passes(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "DEV")
        monkeypatch.setenv(
            "USDC_ASSET_ISSUER",
            "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NOJ4VBH6THS2G2V",
        )
        result = validate_required_env_vars()
        variables = {err.variable for err in result.errors}
        assert "USDC_ASSET_ISSUER" not in variables


class TestAssertValidConfig:
    def test_does_not_raise_in_development(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "DEV")
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN",
        ):
            monkeypatch.delenv(var, raising=False)
        # Should not raise
        assert_valid_config()

    def test_raises_runtime_error_in_production_without_required_vars(self, monkeypatch):
        monkeypatch.setenv("ENV_VERSION", "PROD")
        for var in (
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME",
            "SESSION_SECRET_KEY", "SENTRY_DSN",
        ):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            assert_valid_config()
        # The error message should mention the missing variables
        assert "DB_USER" in str(exc_info.value)
        assert "SESSION_SECRET_KEY" in str(exc_info.value)
