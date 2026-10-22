"""Testes unitários para configurações do geocoding-client (config.py)."""

from geocoding_client.config import ClientSettings


def test_client_settings_default_values():
    """Valida os valores padrão de ClientSettings."""
    settings = ClientSettings(_env_file=None)

    assert settings.geo_api_url == "http://localhost:8004"
    assert settings.geo_api_key == "geocoding_secret_key_change_me"
    assert settings.timeout == 15.0
    assert settings.max_retries == 5
    assert settings.backoff_factor == 2.0


def test_client_settings_custom_values():
    """Valida instanciação com parâmetros customizados."""
    settings = ClientSettings(
        _env_file=None,
        geo_api_url="https://geocoding.meuape.internal:8080",
        geo_api_key="custom_secret_key",
        timeout=30.0,
        max_retries=3,
        backoff_factor=1.5,
    )

    assert settings.geo_api_url == "https://geocoding.meuape.internal:8080"
    assert settings.geo_api_key == "custom_secret_key"
    assert settings.timeout == 30.0
    assert settings.max_retries == 3
    assert settings.backoff_factor == 1.5
