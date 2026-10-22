"""Testes unitários para o roteador de integridade (routers/health.py)."""

from unittest.mock import MagicMock

from fastapi import Request

from src.routers.health import health_check
from src.schemas import HealthResponse


def test_health_check_function_when_model_loaded():
    """Valida retorno da função health_check quando o modelo está carregado."""
    mock_request = MagicMock(spec=Request)
    mock_request.app.state.model = MagicMock()

    response = health_check(mock_request)

    assert isinstance(response, HealthResponse)
    assert response.status == "healthy"
    assert response.model_loaded is True


def test_health_check_function_when_model_is_none():
    """Valida retorno da função health_check quando o modelo é None."""
    mock_request = MagicMock(spec=Request)
    mock_request.app.state.model = None

    response = health_check(mock_request)

    assert isinstance(response, HealthResponse)
    assert response.status == "healthy"
    assert response.model_loaded is False


def test_health_check_function_when_model_attribute_absent():
    """Valida retorno da função health_check quando o atributo model não existe."""
    mock_request = MagicMock(spec=Request)
    del mock_request.app.state.model

    response = health_check(mock_request)

    assert isinstance(response, HealthResponse)
    assert response.status == "healthy"
    assert response.model_loaded is False
