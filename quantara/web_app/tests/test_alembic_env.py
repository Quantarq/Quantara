"""Tests for alembic database URL construction and configuration."""

import os

import pytest


def test_get_database_url_constructs_correctly(monkeypatch):
    """URL is built from the five DB_* env vars."""
    monkeypatch.setenv("DB_USER", "alice")
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t")
    monkeypatch.setenv("DB_HOST", "db.local")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "mydb")

    import importlib
    import web_app.db.database as db_mod
    importlib.reload(db_mod)
    url = db_mod.get_database_url()
    assert url == "postgresql://alice:s3cr3t@db.local:5432/mydb"


def test_get_database_url_default_port(monkeypatch):
    """DB_PORT defaults to 5432 when not set."""
    monkeypatch.setenv("DB_USER", "alice")
    monkeypatch.setenv("DB_PASSWORD", "s3cr3t")
    monkeypatch.setenv("DB_HOST", "db.local")
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.setenv("DB_NAME", "mydb")

    import importlib
    import web_app.db.database as db_mod
    importlib.reload(db_mod)
    url = db_mod.get_database_url()
    assert "5432" in url


def test_alembic_ini_sentinel_value():
    """alembic.ini must not contain the old placeholder URL."""
    ini_path = os.path.join(
        os.path.dirname(__file__), "..", "alembic.ini"
    )
    with open(ini_path) as fh:
        content = fh.read()
    assert "driver://user:pass@localhost/dbname" not in content, (
        "alembic.ini still contains the insecure placeholder URL"
    )
    assert "REPLACE_ME" in content, (
        "alembic.ini must use REPLACE_ME as the sqlalchemy.url sentinel"
    )


def test_get_database_url_includes_all_components(monkeypatch):
    """All components appear in the final URL."""
    monkeypatch.setenv("DB_USER", "myuser")
    monkeypatch.setenv("DB_PASSWORD", "mypass")
    monkeypatch.setenv("DB_HOST", "pghost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "testdb")

    import importlib
    import web_app.db.database as db_mod
    importlib.reload(db_mod)
    url = db_mod.get_database_url()
    assert "myuser" in url
    assert "mypass" in url
    assert "pghost" in url
    assert "5433" in url
    assert "testdb" in url
