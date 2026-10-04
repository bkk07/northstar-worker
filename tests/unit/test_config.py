"""Config loads from env only (Phase 1)."""

import os

from northstar_common.config import Settings, get_settings


def test_defaults_without_env(monkeypatch):
    for key in (
        "APP_NAME",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "BACKEND_HOST",
        "BACKEND_PORT",
        "FRONTEND_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    try:
        settings = Settings()
        assert settings.app_name == "northstar-worker"
        assert settings.backend_port == 8000
    finally:
        get_settings.cache_clear()


def test_env_overrides_defaults(monkeypatch):
    monkeypatch.setenv("BACKEND_PORT", "9001")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    get_settings.cache_clear()
    try:
        settings = Settings()
        assert settings.backend_port == 9001
        assert settings.log_level == "DEBUG"
    finally:
        get_settings.cache_clear()
        os.environ.pop("BACKEND_PORT", None)
        os.environ.pop("LOG_LEVEL", None)
