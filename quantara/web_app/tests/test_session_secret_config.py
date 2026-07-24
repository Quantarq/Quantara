"""Session secret configuration guards."""

from pathlib import Path

from web_app.config_validator import validate_required_env_vars


_REQUIRED_PROD_ENV = {
    "DB_USER": "quantara",
    "DB_PASSWORD": "secret-password",
    "DB_HOST": "db",
    "DB_NAME": "quantara",
    "SENTRY_DSN": "https://example.invalid/1",
}


def _set_required_prod_env(monkeypatch):
    monkeypatch.setenv("ENV_VERSION", "PROD")
    for key, value in _REQUIRED_PROD_ENV.items():
        monkeypatch.setenv(key, value)


def _errors_by_variable(result):
    return {error.variable: error.message for error in result.errors}


def test_production_requires_session_secret(monkeypatch):
    _set_required_prod_env(monkeypatch)
    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)

    errors = _errors_by_variable(validate_required_env_vars(is_production=True))

    assert "SESSION_SECRET_KEY" in errors
    assert "not set" in errors["SESSION_SECRET_KEY"]


def test_production_rejects_short_session_secret(monkeypatch):
    _set_required_prod_env(monkeypatch)
    monkeypatch.setenv("SESSION_SECRET_KEY", "short")

    errors = _errors_by_variable(validate_required_env_vars(is_production=True))

    assert "SESSION_SECRET_KEY" in errors
    assert "at least 32 characters" in errors["SESSION_SECRET_KEY"]


def test_production_accepts_configured_session_secret(monkeypatch):
    _set_required_prod_env(monkeypatch)
    monkeypatch.setenv("SESSION_SECRET_KEY", "a" * 64)

    errors = _errors_by_variable(validate_required_env_vars(is_production=True))

    assert "SESSION_SECRET_KEY" not in errors


def test_main_does_not_use_random_session_secret_in_production():
    main_source = Path(__file__).resolve().parents[1] / "api" / "main.py"
    source = main_source.read_text(encoding="utf-8")

    assert 'os.getenv("SESSION_SECRET_KEY", os.urandom' not in source
    assert 'if os.getenv("ENV_VERSION") == "PROD"' in source
    assert 'raise RuntimeError("SESSION_SECRET_KEY must be set in production.")' in source