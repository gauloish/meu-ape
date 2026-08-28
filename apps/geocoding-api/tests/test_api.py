from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from src.dependencies import get_db, get_http_client
from src.main import app

VALID_API_KEY = "geocoding_secret_key_change_me"


async def mock_get_db():
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock()
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


def test_protected_endpoint_with_valid_api_key(client: TestClient):
    """Valida que requisição com X-API-Key correta passa pela autenticação."""
    app.dependency_overrides[get_http_client] = mock_http_client_factory
    app.dependency_overrides[get_db] = mock_get_db
    try:
        headers = {"X-API-Key": VALID_API_KEY}
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


def test_rate_limiting(client: TestClient):
    """Valida que exceder o rate limit dispara HTTP 429 Too Many Requests."""
    app.dependency_overrides[get_http_client] = mock_http_client_factory
    app.dependency_overrides[get_db] = mock_get_db
    headers = {"X-API-Key": VALID_API_KEY}
    responses = []
    try:
        for _ in range(110):
            res = client.get("/geocoding/search?address=Teste", headers=headers)
            responses.append(res.status_code)
    finally:
        app.dependency_overrides.clear()

    assert 429 in responses


if __name__ == "__main__":
    print("Iniciando suíte de testes de integração da geocoding-api...")
    with TestClient(app) as client:
        test_health_endpoint_is_public(client)
        print("[PASS] test_health_endpoint_is_public")
        test_protected_endpoint_without_api_key(client)
        print("[PASS] test_protected_endpoint_without_api_key")
        test_protected_endpoint_with_invalid_api_key(client)
        print("[PASS] test_protected_endpoint_with_invalid_api_key")
        test_protected_endpoint_with_valid_api_key(client)
        print("[PASS] test_protected_endpoint_with_valid_api_key")
        test_batch_search_without_api_key(client)
        print("[PASS] test_batch_search_without_api_key")
        test_batch_reverse_without_api_key(client)
        print("[PASS] test_batch_reverse_without_api_key")
        test_rate_limiting(client)
        print("[PASS] test_rate_limiting")
    print("Todos os testes passaram com sucesso!")
