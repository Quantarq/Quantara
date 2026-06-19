"""
Tests for the FastAPI CORS configuration.
"""

from starlette.middleware.cors import CORSMiddleware

from web_app.api.main import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    DEFAULT_CORS_ORIGINS,
    app,
    get_cors_origins,
)


def test_cors_origins_default_to_localhost_when_unset(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert get_cors_origins() == DEFAULT_CORS_ORIGINS


def test_cors_origins_are_trimmed_and_split(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        " https://quantara.xyz , http://localhost:3000 , https://app.quantara.xyz ",
    )

    assert get_cors_origins() == [
        "https://quantara.xyz",
        "http://localhost:3000",
        "https://app.quantara.xyz",
    ]


def test_blank_cors_origins_fall_back_to_localhost(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " , ")

    assert get_cors_origins() == DEFAULT_CORS_ORIGINS


def test_app_registers_restricted_cors_policy():
    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == DEFAULT_CORS_ORIGINS
    assert cors_middleware.kwargs["allow_methods"] == CORS_ALLOW_METHODS
    assert cors_middleware.kwargs["allow_headers"] == CORS_ALLOW_HEADERS
