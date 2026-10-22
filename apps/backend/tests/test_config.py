"""Testes unitários para o módulo de configurações da aplicação (config.py)."""

from pathlib import Path

import pytest

from src.config import Settings


def test_settings_default_values():
    """Valida os valores padrão das configurações da aplicação."""
    settings = Settings(_env_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 8001
    assert settings.model_filename == "model.joblib"
    assert settings.log_level == "INFO"
    assert settings.cors_origins == "*"
    assert settings.hf_token is None
    assert settings.repo_id == ""
    assert settings.hf_cache_dir is None


def test_settings_custom_values(tmp_path: Path):
    """Valida a instanciação de Settings com parâmetros customizados."""
    custom_cache = tmp_path / "custom_hf_cache"
    settings = Settings(
        _env_file=None,
        host="127.0.0.1",
        port=9000,
        model_filename="custom_model.joblib",
        log_level="DEBUG",
        cors_origins="https://meuape.com.br, http://localhost:3000",
        hf_token="hf_test_token_123",
        repo_id="usuario/meu-ape-xgboost",
        hf_cache_dir=custom_cache,
    )

    assert settings.host == "127.0.0.1"
    assert settings.port == 9000
    assert settings.model_filename == "custom_model.joblib"
    assert settings.log_level == "DEBUG"
    assert settings.hf_token == "hf_test_token_123"
    assert settings.repo_id == "usuario/meu-ape-xgboost"
    assert settings.hf_cache_dir == custom_cache


@pytest.mark.parametrize(
    ("raw_cors", "expected_list"),
    [
        ("*", ["*"]),
        (" * ", ["*"]),
        ("", ["*"]),
        ("   ", []),
        ("https://meuape.com.br", ["https://meuape.com.br"]),
        (
            "https://meuape.com.br, http://localhost:3000",
            ["https://meuape.com.br", "http://localhost:3000"],
        ),
        (
            "https://meuape.com.br, , http://localhost:3000, ",
            ["https://meuape.com.br", "http://localhost:3000"],
        ),
    ],
)
def test_cors_origins_list_parsing(raw_cors: str, expected_list: list[str]):
    """Valida a conversão da string de origens CORS para lista higienizada."""
    settings = Settings(_env_file=None, cors_origins=raw_cors)
    assert settings.cors_origins_list == expected_list
