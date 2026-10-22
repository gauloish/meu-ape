"""Testes automatizados dos endpoints HTTP e contratos de API do Backend."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.main import app
from src.routers.prediction import request_to_dataframe
from src.schemas import InferenceRequest


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


def test_health_check_endpoint(client: TestClient):
    """Testa a rota GET /health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data


def test_health_check_endpoint_model_loaded(client: TestClient):
    """Testa GET /health quando o modelo de ML está carregado em memória."""
    app.state.model = MagicMock()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    app.state.model = None


def test_health_check_endpoint_model_not_loaded(client: TestClient):
    """Testa GET /health quando o modelo de ML não está carregado."""
    app.state.model = None
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is False


def test_predict_endpoint_model_unavailable(client: TestClient):
    """Garante que a rota /predict retorna 503 se o modelo não estiver em memória."""
    app.state.model = None
    response = client.post("/predict", json=get_sample_payload())
    assert response.status_code == 503
    assert "não está carregado" in response.json()["detail"]


def test_predict_endpoint_successful(client: TestClient):
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
    app.state.model = None


def test_predict_endpoint_with_all_features(
    client: TestClient, valid_payload_all_features: dict
):
    """Testa a rota /predict com todas as 28 variáveis booleanas e coordenadas geográficas."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([2450000.0])
    app.state.model = mock_model

    response = client.post("/predict", json=valid_payload_all_features)

    assert response.status_code == 200
    data = response.json()
    assert data["estimated_price"] == 2450000.0
    assert data["currency"] == "BRL"
    app.state.model = None


def test_predict_endpoint_model_inference_exception(client: TestClient):
    """Testa se a rota /predict retorna status 500 caso o modelo dispare exceção interna."""
    mock_model = MagicMock()
    mock_model.predict.side_effect = RuntimeError("Erro interno no pipeline XGBoost")
    app.state.model = mock_model

    response = client.post("/predict", json=get_sample_payload())

    assert response.status_code == 500
    data = response.json()
    assert "Falha ao processar inferência do modelo" in data["detail"]
    app.state.model = None


def test_predict_endpoint_validation_error(client: TestClient):
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
    app.state.model = None


def test_predict_endpoint_boundary_coordinates(client: TestClient):
    """Garante aceitação de coordenadas nos limites exatos do bounding box de Goiânia."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([500000.0])
    app.state.model = mock_model

    payload = get_sample_payload()
    payload["latitude"] = -16.85  # MIN_LATITUDE
    payload["longitude"] = -49.45  # MIN_LONGITUDE

    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    app.state.model = None


def test_predict_endpoint_out_of_bounds_coordinates(client: TestClient):
    """Garante retorno de erro 422 para coordenadas fora do município de Goiânia."""
    app.state.model = MagicMock()

    payload = get_sample_payload()
    payload["latitude"] = -23.55  # São Paulo (fora de Goiânia)
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    payload["latitude"] = -16.68
    payload["longitude"] = -46.63  # Fora de Goiânia
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
    app.state.model = None


def test_predict_endpoint_negative_numeric_values(client: TestClient):
    """Garante retorno de erro 422 para valores numéricos negativos ou fora dos limites."""
    app.state.model = MagicMock()

    payload = get_sample_payload()
    payload["condominio"] = -10
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    payload = get_sample_payload()
    payload["area_m2"] = 15  # Abaixo do limite ge=20
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

    payload = get_sample_payload()
    payload["quartos"] = 9  # Acima do limite le=8
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
    app.state.model = None


def test_docs_endpoint(client: TestClient):
    """Valida disponibilidade da documentação interativa OpenAPI/Swagger UI."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_openapi_schema_endpoint(client: TestClient):
    """Valida disponibilidade do schema OpenAPI JSON da aplicação."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/predict" in data["paths"]


def test_cors_preflight_request(client: TestClient):
    """Valida comportamento do middleware CORS para requisições com header Origin."""
    response = client.options(
        "/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
