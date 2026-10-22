"""Testes unitários para as funções e limitadores de requisição (Rate Limiter)."""

from unittest.mock import MagicMock

from src.config import settings
from src.rate_limiter import (
    get_rate_limit_batch,
    get_rate_limit_default,
    get_remote_address_or_api_key,
)


def test_get_remote_address_or_api_key_with_header():
    """Valida identificador de rate limit baseado na X-API-Key quando presente no cabeçalho."""
    request = MagicMock()
    request.headers.get.return_value = "my_custom_api_key"

    identifier = get_remote_address_or_api_key(request)
    assert identifier == "key:my_custom_api_key"


def test_get_remote_address_or_api_key_fallback_ip(monkeypatch):
    """Valida fallback para IP do cliente quando X-API-Key não é informada."""
    request = MagicMock()
    request.headers.get.return_value = None
    monkeypatch.setattr(
        "src.rate_limiter.get_remote_address", lambda req: "192.168.1.100"
    )

    identifier = get_remote_address_or_api_key(request)
    assert identifier == "ip:192.168.1.100"


def test_get_rate_limit_default_tier_resolution():
    """Valida resolução de limites unitários dinamicamente para perfis ML e APP."""
    ml_key_ident = f"key:{settings.geo_api_key_ml}"
    app_key_ident = f"key:{settings.geo_api_key_app}"
    generic_ident = "ip:127.0.0.1"

    assert get_rate_limit_default(ml_key_ident) == settings.rate_limit_ml_default
    assert get_rate_limit_default(app_key_ident) == settings.rate_limit_app_default
    assert get_rate_limit_default(generic_ident) == settings.rate_limit_app_default


def test_get_rate_limit_batch_tier_resolution():
    """Valida resolução de limites em lote dinamicamente para perfis ML e APP."""
    ml_key_ident = f"key:{settings.geo_api_key_ml}"
    app_key_ident = f"key:{settings.geo_api_key_app}"
    generic_ident = "ip:127.0.0.1"

    assert get_rate_limit_batch(ml_key_ident) == settings.rate_limit_ml_batch
    assert get_rate_limit_batch(app_key_ident) == settings.rate_limit_app_batch
    assert get_rate_limit_batch(generic_ident) == settings.rate_limit_app_batch
