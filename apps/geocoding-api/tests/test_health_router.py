"""Testes unitários e de integração HTTP para o endpoint de integridade /health."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


def test_health_check_all_services_online(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa o status HTTP 200 (online) quando banco e Nominatim respondem com sucesso."""
    # DB responde SELECT 1
    mock_db_res = MagicMock()
    mock_db_res.scalar.return_value = 1
    mock_db_session.execute.return_value = mock_db_res

    # Nominatim responde 200 no /status
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_http_client.get.return_value = mock_resp

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] is True
    assert data["nominatim"] is True
    assert "operacionais" in data["message"]


def test_health_check_database_down(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa status HTTP 503 (degraded) quando o banco de dados falha."""
    mock_db_session.execute.side_effect = RuntimeError("Conexão recusada no banco")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_http_client.get.return_value = mock_resp

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] is False
    assert data["nominatim"] is True


def test_health_check_nominatim_fallback_success(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa status HTTP 200 quando o endpoint /status falha mas o fallback /search responde 200."""
    mock_db_res = MagicMock()
    mock_db_res.scalar.return_value = 1
    mock_db_session.execute.return_value = mock_db_res

    resp_fail = MagicMock(status_code=404)
    resp_success = MagicMock(status_code=200)
    mock_http_client.get.side_effect = [resp_fail, resp_success]

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["nominatim"] is True


def test_health_check_all_services_offline(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa status HTTP 503 (offline) quando banco e Nominatim estão indisponíveis."""
    mock_db_session.execute.side_effect = RuntimeError("DB down")
    mock_http_client.get.side_effect = RuntimeError("Network error")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "offline"
    assert data["database"] is False
    assert data["nominatim"] is False
