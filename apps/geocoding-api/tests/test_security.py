"""Testes unitários para autenticação e verificação de chaves de API na geocoding-api."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.config import settings
from src.security import verify_api_key


def test_verify_api_key_missing_raises_401():
    """Garante que a ausência do cabeçalho X-API-Key dispara HTTP 401."""
    request = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(request=request, api_key=None))

    assert exc_info.value.status_code == 401
    assert "inválida ou ausente" in exc_info.value.detail


def test_verify_api_key_invalid_raises_401():
    """Garante que uma chave inválida dispara HTTP 401."""
    request = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_api_key(request=request, api_key="chave_invalida_123"))

    assert exc_info.value.status_code == 401
    assert "inválida ou ausente" in exc_info.value.detail


def test_verify_api_key_app_tier():
    """Valida autenticação com chave de consumo padrão (APP) atribuindo o tier 'app'."""
    request = MagicMock()
    request.state = MagicMock()

    returned_key = asyncio.run(
        verify_api_key(request=request, api_key=settings.geo_api_key_app)
    )
    assert returned_key == settings.geo_api_key_app
    assert request.state.client_tier == "app"


def test_verify_api_key_ml_tier():
    """Valida autenticação com chave de alta vazão (ML) atribuindo o tier 'ml'."""
    request = MagicMock()
    request.state = MagicMock()

    returned_key = asyncio.run(
        verify_api_key(request=request, api_key=settings.geo_api_key_ml)
    )
    assert returned_key == settings.geo_api_key_ml
    assert request.state.client_tier == "ml"
