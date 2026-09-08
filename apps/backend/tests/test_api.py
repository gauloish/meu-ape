"""Testes automatizados dos endpoints e da conversão de dados do Backend."""

from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routers.prediction import request_to_dataframe
from src.schemas import InferenceRequest


@pytest.fixture
def client():
    """Fixture que cria o TestClient para a aplicação FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


def get_sample_payload() -> dict:
    """Retorna um payload de exemplo válido para o InferenceRequest."""
    return {
        "tipo_imovel": "apartamento",
        "condominio": 650,
        "area_m2": 85,
        "quartos": 3,
        "banheiros": 2,
        "vagas": 2,
        "piscina": True,
        "academia": True,
        "latitude": -16.68,
        "longitude": -49.25,
    }


def test_request_to_dataframe():
    """Garante que o schema Pydantic é convertido corretamente em um pandas DataFrame."""
    payload_data = get_sample_payload()
    request = InferenceRequest(**payload_data)
    df = request_to_dataframe(request)

    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 1
    assert "area_m2" in df.columns
    assert "quartos" in df.columns
    assert "tipo_imovel" in df.columns
    assert df["area_m2"].iloc[0] == 85
    assert df["quartos"].iloc[0] == 3


def test_health_check_endpoint(client):
    """Testa a rota GET /health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data


def test_predict_endpoint_model_unavailable(client):
    """Garante que a rota /predict retorna 503 se o modelo não estiver em memória."""
    app.state.model = None
    response = client.post("/predict", json=get_sample_payload())
    assert response.status_code == 503
    assert "não está carregado" in response.json()["detail"]


def test_predict_endpoint_successful(client):
    """Testa a rota /predict quando o modelo está carregado em memória."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1250000.0])

    app.state.model = mock_model

    response = client.post("/predict", json=get_sample_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["estimated_price"] == 1250000.0
    assert data["currency"] == "BRL"
    mock_model.predict.assert_called_once()


def test_predict_endpoint_validation_error(client):
    """Garante retorno de erro 422 caso os campos obrigatórios sejam inválidos ou ausentes."""
    app.state.model = MagicMock()

    # Envia payload vazio
    response = client.post("/predict", json={})
    assert response.status_code == 422

    # Envia tipo_imovel inválido
    invalid_payload = get_sample_payload()
    invalid_payload["tipo_imovel"] = "invalido_inexistente"
    response = client.post("/predict", json=invalid_payload)
    assert response.status_code == 422
