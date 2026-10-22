"""Testes unitários para as configurações e variáveis de ambiente da geocoding-api."""

import pytest

from src.config import Settings


def test_settings_default_values():
    """Valida os valores padrão de configuração da API e limites de rate limit."""
    cfg = Settings(_env_file=None)

    assert cfg.postgres_user == "user"
    assert cfg.postgres_password == "password"
    assert cfg.postgres_host == "cache_db"
    assert cfg.postgres_port == 5432
    assert cfg.postgres_db == "geocoding_database"

    assert cfg.db_pool_size == 10
    assert cfg.db_max_overflow == 20
    assert cfg.db_pool_recycle == 1800

    assert cfg.nominatim_url == "http://nominatim_server:8080"
    assert cfg.user_agent == "GeocodingAPI/1.0"
    assert cfg.log_level == "INFO"

    assert cfg.geo_api_key_app == "geocoding_secret_key_change_me"
    assert cfg.geo_api_key_ml == "geocoding_ml_secret_key_change_me"

    assert cfg.rate_limit_app_default == "60/minute"
    assert cfg.rate_limit_app_batch == "10/minute"
    assert cfg.rate_limit_ml_default == "600/minute"
    assert cfg.rate_limit_ml_batch == "120/minute"


def test_settings_database_url_property():
    """Valida a geração da URL assíncrona do PostgreSQL com asyncpg."""
    cfg = Settings(
        postgres_user="custom_user",
        postgres_password="custom_password",
        postgres_host="localhost",
        postgres_port=5433,
        postgres_db="custom_db",
    )

    expected_url = (
        "postgresql+asyncpg://custom_user:custom_password@localhost:5433/custom_db"
    )
    assert cfg.database_url == expected_url


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch):
    """Valida a sobrescrita de configurações a partir de variáveis de ambiente."""
    monkeypatch.setenv("POSTGRES_HOST", "postgres.production.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("GEO_API_KEY_APP", "super_secret_app_key")
    monkeypatch.setenv("RATE_LIMIT_APP_DEFAULT", "120/minute")

    cfg = Settings()
    assert cfg.postgres_host == "postgres.production.internal"
    assert cfg.geo_api_key_app == "super_secret_app_key"
    assert cfg.rate_limit_app_default == "120/minute"
