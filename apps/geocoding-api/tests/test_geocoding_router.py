"""Suíte de testes de integração HTTP para os endpoints /geocoding da geocoding-api."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
from fastapi.testclient import TestClient

from src.config import settings
from src.database.models import GeocodingCache, ReverseGeocodingCache

AUTH_HEADERS_APP = {"X-API-Key": settings.geo_api_key_app}
AUTH_HEADERS_ML = {"X-API-Key": settings.geo_api_key_ml}


# ==============================================================================
# GET /geocoding/search Tests
# ==============================================================================


def test_search_address_unauthorized(client: TestClient):
    """Garante que requisições sem API Key ou com chave inválida recebem HTTP 401."""
    # Sem cabeçalho
    resp_no_key = client.get("/geocoding/search?address=Avenida+Anhanguera")
    assert resp_no_key.status_code == 401

    # Com chave incorreta
    resp_bad_key = client.get(
        "/geocoding/search?address=Avenida+Anhanguera",
        headers={"X-API-Key": "chave_incorreta"},
    )
    assert resp_bad_key.status_code == 401


def test_search_address_cache_hit(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Valida retorno imediato a partir do cache sem acionar o Nominatim."""
    cached_record = GeocodingCache(
        address="avenida anhanguera",
        latitude=-16.6868,
        longitude=-49.2648,
        formatted_address="Avenida Anhanguera, Goiânia, GO",
        place_id="12345",
    )
    mock_db_session.get.return_value = cached_record

    response = client.get(
        "/geocoding/search?address=Avenida+Anhanguera", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "cache"
    assert data["data"]["latitude"] == -16.6868
    assert data["data"]["longitude"] == -49.2648
    # Nominatim não deve ser chamado
    assert mock_http_client.get.call_count == 0


def test_search_address_cache_miss_nominatim_success(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Valida consulta ao Nominatim em caso de Cache MISS e persistência no banco."""
    mock_db_session.get.return_value = None  # Cache MISS

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [
        {
            "lat": "-16.70",
            "lon": "-49.27",
            "place_id": "555",
            "display_name": "Rua T-55, Setor Bueno, Goiânia, GO",
        }
    ]
    mock_http_client.get.return_value = mock_resp

    response = client.get(
        "/geocoding/search?address=Rua+T-55", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "nominatim"
    assert data["data"]["latitude"] == -16.70
    assert data["data"]["place_id"] == "555"

    # Deve salvar no cache via execute
    assert mock_db_session.execute.call_count >= 1


def test_search_address_cache_miss_nominatim_not_found(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Valida HTTP 404 quando o Nominatim não localiza o endereço buscado."""
    mock_db_session.get.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = []  # Lista vazia
    mock_http_client.get.return_value = mock_resp

    response = client.get(
        "/geocoding/search?address=Endereco+Inexistente",
        headers=AUTH_HEADERS_APP,
    )
    assert response.status_code == 404
    assert "não encontrado" in response.json()["detail"]


def test_search_address_nominatim_request_error(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Valida HTTP 502 quando ocorre falha física de conexão com o Nominatim."""
    mock_db_session.get.return_value = None
    mock_http_client.get.side_effect = httpx.RequestError("Conexão falhou")

    response = client.get(
        "/geocoding/search?address=Avenida+85", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 502
    assert "indisponível" in response.json()["detail"]


# ==============================================================================
# POST /geocoding/search/batch Tests
# ==============================================================================


def test_batch_search_address_mixed(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa busca em lote com parte dos endereços em cache e parte consultando o Nominatim."""
    cached_record = GeocodingCache(
        address="rua 1",
        latitude=-16.1,
        longitude=-49.1,
        formatted_address="Rua 1, Goiânia",
        place_id="101",
    )
    # Cache retorna Rua 1
    mock_exec_res = MagicMock()
    mock_exec_res.scalars.return_value.all.return_value = [cached_record]
    mock_db_session.execute.return_value = mock_exec_res

    # Nominatim retorna Rua 2
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [
        {"lat": "-16.2", "lon": "-49.2", "place_id": "102", "display_name": "Rua 2"}
    ]
    mock_http_client.get.return_value = mock_resp

    payload = {"addresses": ["Rua 1", "Rua 2"]}
    response = client.post(
        "/geocoding/search/batch", json=payload, headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["source"] == "cache"
    assert data["results"][1]["source"] == "nominatim"


def test_batch_search_address_nominatim_error_handling(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Garante que falhas no Nominatim para um endereço resultem em source='error' sem quebrar o lote."""
    mock_exec_res = MagicMock()
    mock_exec_res.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_exec_res

    # Nominatim lança exceção
    mock_http_client.get.side_effect = RuntimeError("Falha de rede")

    payload = {"addresses": ["Rua Falha"]}
    response = client.post(
        "/geocoding/search/batch", json=payload, headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "error"


# ==============================================================================
# GET /geocoding/reverse Tests
# ==============================================================================


def test_reverse_geocode_cache_hit(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa geocodificação reversa atendida pelo cache."""
    cached = ReverseGeocodingCache(
        coord_key="-16.68000,-49.25000",
        latitude=-16.68,
        longitude=-49.25,
        raw_data_json=json.dumps({"road": "Avenida Anhanguera"}),
    )
    mock_db_session.get.return_value = cached

    response = client.get(
        "/geocoding/reverse?lat=-16.68&lon=-49.25", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "cache"
    assert data["data"]["road"] == "Avenida Anhanguera"
    assert mock_http_client.get.call_count == 0


def test_reverse_geocode_cache_miss_nominatim_success(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa geocodificação reversa buscando no Nominatim e salvando no cache."""
    mock_db_session.get.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"road": "Rua T-63", "city": "Goiânia"}
    mock_http_client.get.return_value = mock_resp

    response = client.get(
        "/geocoding/reverse?lat=-16.71&lon=-49.27", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "nominatim"
    assert data["data"]["road"] == "Rua T-63"


def test_reverse_geocode_nominatim_error_payload(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa HTTP 404 quando o Nominatim retorna chave de erro na resposta."""
    mock_db_session.get.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"error": "Unable to geocode"}
    mock_http_client.get.return_value = mock_resp

    response = client.get(
        "/geocoding/reverse?lat=0.0&lon=0.0", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 404


def test_reverse_geocode_nominatim_request_error(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa HTTP 502 quando ocorre falha de conexão no reverse geocode."""
    mock_db_session.get.return_value = None
    mock_http_client.get.side_effect = httpx.RequestError("Timeout")

    response = client.get(
        "/geocoding/reverse?lat=-16.68&lon=-49.25", headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 502


# ==============================================================================
# POST /geocoding/reverse/batch Tests
# ==============================================================================


def test_batch_reverse_geocode_mixed(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Testa geocodificação reversa em lote com mix de cache e Nominatim."""
    key1 = ReverseGeocodingCache.make_key(-16.1, -49.1)
    cached_rec = ReverseGeocodingCache(
        coord_key=key1,
        latitude=-16.1,
        longitude=-49.1,
        raw_data_json=json.dumps({"road": "Rua 1"}),
    )
    mock_exec_res = MagicMock()
    mock_exec_res.scalars.return_value.all.return_value = [cached_rec]
    mock_db_session.execute.return_value = mock_exec_res

    # Nominatim responde coord 2
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"road": "Rua 2"}
    mock_http_client.get.return_value = mock_resp

    payload = {
        "coordinates": [
            {"latitude": -16.1, "longitude": -49.1},
            {"latitude": -16.2, "longitude": -49.2},
        ]
    }
    response = client.post(
        "/geocoding/reverse/batch", json=payload, headers=AUTH_HEADERS_APP
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["source"] == "cache"
    assert data["results"][1]["source"] == "nominatim"


# ==============================================================================
# Rate Limiting Tier Differences Test
# ==============================================================================


def test_rate_limiting_tier_differences(
    client: TestClient, mock_db_session: AsyncMock, mock_http_client: AsyncMock
):
    """Valida que o perfil APP sofre rate limit em lote (10/min) enquanto o perfil ML suporta maior vazão."""
    payload = {"addresses": ["Endereço 1"]}

    # Chave APP: limite batch é 10/minuto -> após 10 requisições dispara 429
    app_responses = [
        client.post(
            "/geocoding/search/batch", json=payload, headers=AUTH_HEADERS_APP
        ).status_code
        for _ in range(12)
    ]
    assert 429 in app_responses

    # Chave ML: limite batch é 120/minuto -> requisições passam com 200
    ml_responses = [
        client.post(
            "/geocoding/search/batch", json=payload, headers=AUTH_HEADERS_ML
        ).status_code
        for _ in range(12)
    ]
    assert all(code == 200 for code in ml_responses)
