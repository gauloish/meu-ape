import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.config import settings
from src.dependencies import get_db, get_http_client
from src.main import app

VALID_APP_API_KEY = settings.geo_api_key_app
VALID_ML_API_KEY = settings.geo_api_key_ml


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


async def mock_get_db():
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock()
    yield mock_session


def mock_http_client_factory():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(
        return_value=[{"lat": "-16.68", "lon": "-49.25", "place_id": "123", "display_name": "Goiânia, GO"}]
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


def test_health_endpoint_is_public(client: TestClient):
    """Valida que o endpoint /health é público (não exige X-API-Key)."""
    response = client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "nominatim" in data


def test_protected_endpoint_without_api_key(client: TestClient):
    """Valida que rotas protegidas sem X-API-Key retornam HTTP 401."""
    response = client.get("/geocoding/search?address=Avenida+Anhanguera")
    assert response.status_code == 401
    assert response.json()["detail"] == "Chave de API (X-API-Key) inválida ou ausente."


def test_protected_endpoint_with_invalid_api_key(client: TestClient):
    """Valida que rotas protegidas com X-API-Key incorreta retornam HTTP 401."""
    headers = {"X-API-Key": "chave_totalmente_invalida"}
    response = client.get("/geocoding/search?address=Avenida+Anhanguera", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Chave de API (X-API-Key) inválida ou ausente."


def test_protected_endpoint_with_valid_app_api_key(client: TestClient):
    """Valida que requisição com a chave APP passa pela autenticação com perfil app."""
    app.dependency_overrides[get_http_client] = mock_http_client_factory
    app.dependency_overrides[get_db] = mock_get_db
    try:
        headers = {"X-API-Key": VALID_APP_API_KEY}
        response = client.get("/geocoding/search?address=Avenida+Anhanguera", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "nominatim"
        assert data["data"]["place_id"] == "123"
    finally:
        app.dependency_overrides.clear()


def test_protected_endpoint_with_valid_ml_api_key(client: TestClient):
    """Valida que requisição com a chave ML passa pela autenticação com perfil ml."""
    app.dependency_overrides[get_http_client] = mock_http_client_factory
    app.dependency_overrides[get_db] = mock_get_db
    try:
        headers = {"X-API-Key": VALID_ML_API_KEY}
        response = client.get("/geocoding/search?address=Avenida+Anhanguera", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "nominatim"
        assert data["data"]["place_id"] == "123"
    finally:
        app.dependency_overrides.clear()


def test_batch_search_without_api_key(client: TestClient):
    """Valida proteção no endpoint batch sem API Key."""
    payload = {"addresses": ["Endereço 1", "Endereço 2"]}
    response = client.post("/geocoding/search/batch", json=payload)
    assert response.status_code == 401


def test_batch_reverse_without_api_key(client: TestClient):
    """Valida proteção no endpoint reverse batch sem API Key."""
    payload = {"coordinates": [{"latitude": -16.68, "longitude": -49.25}]}
    response = client.post("/geocoding/reverse/batch", json=payload)
    assert response.status_code == 401


def test_rate_limiting_tier_differences(client: TestClient):
    """Valida que o perfil APP sofre rate limit em lote mais rápido (10/min) que o perfil ML (120/min)."""
    app.dependency_overrides[get_http_client] = mock_http_client_factory
    app.dependency_overrides[get_db] = mock_get_db
    payload = {"addresses": ["Endereço 1"]}
    try:
        # Chave APP: limite batch é 10/minuto -> após 10 requisições dispara 429
        headers_app = {"X-API-Key": VALID_APP_API_KEY}
        app_responses = [client.post("/geocoding/search/batch", json=payload, headers=headers_app).status_code for _ in range(12)]
        assert 429 in app_responses

        # Chave ML: limite batch é 120/minuto -> 12 requisições passam todas com 200
        headers_ml = {"X-API-Key": VALID_ML_API_KEY}
        ml_responses = [client.post("/geocoding/search/batch", json=payload, headers=headers_ml).status_code for _ in range(12)]
        assert all(code == 200 for code in ml_responses)
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    print("Iniciando suíte de testes de integração da geocoding-api...")
    with TestClient(app) as client:
        test_health_endpoint_is_public(client)
        print("[PASS] test_health_endpoint_is_public")
        test_protected_endpoint_without_api_key(client)
        print("[PASS] test_protected_endpoint_without_api_key")
        test_protected_endpoint_with_invalid_api_key(client)
        print("[PASS] test_protected_endpoint_with_invalid_api_key")
        test_protected_endpoint_with_valid_app_api_key(client)
        print("[PASS] test_protected_endpoint_with_valid_app_api_key")
        test_protected_endpoint_with_valid_ml_api_key(client)
        print("[PASS] test_protected_endpoint_with_valid_ml_api_key")
        test_batch_search_without_api_key(client)
        print("[PASS] test_batch_search_without_api_key")
        test_batch_reverse_without_api_key(client)
        print("[PASS] test_batch_reverse_without_api_key")
        test_rate_limiting_tier_differences(client)
        print("[PASS] test_rate_limiting_tier_differences")
    print("Todos os testes passaram com sucesso!")
