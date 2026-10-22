"""Testes unitários para as dependências compartilhadas do FastAPI (dependencies.py)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request, status

from src.dependencies import get_model


def test_get_model_success():
    """Valida retorno do modelo quando instanciado no estado da aplicação."""
    mock_request = MagicMock(spec=Request)
    mock_model = MagicMock()
    mock_request.app.state.model = mock_model

    result = get_model(mock_request)

    assert result is mock_model


def test_get_model_raises_503_when_model_is_none():
    """Valida lançamento de HTTP 503 quando app.state.model é None."""
    mock_request = MagicMock(spec=Request)
    mock_request.app.state.model = None

    with pytest.raises(HTTPException) as exc_info:
        get_model(mock_request)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "não está carregado" in exc_info.value.detail


def test_get_model_raises_503_when_model_attribute_missing():
    """Valida lançamento de HTTP 503 quando o atributo model não existe no state."""
    mock_request = MagicMock(spec=Request)
    # Garante que hasattr(mock_request.app.state, "model") retorna False
    del mock_request.app.state.model

    with pytest.raises(HTTPException) as exc_info:
        get_model(mock_request)

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "não está carregado" in exc_info.value.detail
