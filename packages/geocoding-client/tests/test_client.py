import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from geocoding_client import (
    GeocodingClient,
    AuthenticationError,
    AddressNotFound,
    RateLimitExceeded,
    ServerError,
    CoordinateRequest,
)

VALID_KEY = "test_secret_key"


def test_client_init_and_env():
    """Testa inicialização do cliente com valores customizados e defaults."""
    client = GeocodingClient(base_url="http://api.test:8000/", api_key="minha_chave")
    assert client.base_url == "http://api.test:8000"
    assert client.api_key == "minha_chave"
    assert client._headers["X-API-Key"] == "minha_chave"


def test_client_header_injection():
    """Testa se o cabeçalho X-API-Key é injetado nas requisições."""
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "source": "cache",
        "data": {
            "place_id": "1",
            "address": "Rua 1",
            "latitude": -16.68,
            "longitude": -49.25,
            "formatted_address": "Rua 1, Goiânia",
        },
    }

    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(api_key=VALID_KEY, http_client=mock_httpx)
    result = asyncio.run(client.geocode("Rua 1"))

    assert result.source == "cache"
    assert result.data.latitude == -16.68
    assert mock_httpx.request.call_count == 1


def test_exception_mapping_401():
    """Testa lançamento de AuthenticationError em HTTP 401."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"detail": "API Key inválida."}

    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    try:
        asyncio.run(client.geocode("Rua 1"))
        assert False, "Deveria ter lançado AuthenticationError"
    except AuthenticationError as exc:
        assert exc.status_code == 401
        assert "API Key inválida" in str(exc)


def test_exception_mapping_404():
    """Testa lançamento de AddressNotFound em HTTP 404."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"detail": "Endereço não encontrado."}

    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    try:
        asyncio.run(client.geocode("Rua Inexistente"))
        assert False, "Deveria ter lançado AddressNotFound"
    except AddressNotFound as exc:
        assert exc.status_code == 404


def test_batch_geocode_and_backoff_retry():
    """Testa requisição em lote com retentativa por RateLimit (429) via Backoff."""
    resp_429 = MagicMock()
    resp_429.is_success = False
    resp_429.status_code = 429
    resp_429.headers = {}
    resp_429.json.return_value = {"detail": "Rate limit exceeded"}

    resp_200 = MagicMock()
    resp_200.is_success = True
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "results": [
            {
                "source": "nominatim",
                "data": {
                    "place_id": "10",
                    "address": "Av T-63",
                    "latitude": -16.71,
                    "longitude": -49.26,
                    "formatted_address": "Av T-63, Goiânia",
                },
            }
        ]
    }

    mock_httpx = AsyncMock()
    # Primeira chamada retorna 429, segunda chamada retorna 200
    mock_httpx.request = AsyncMock(side_effect=[resp_429, resp_200])

    client = GeocodingClient(http_client=mock_httpx)

    # Reduz o tempo de espera do retry durante os testes
    client.settings.backoff_factor = 0.01

    res = asyncio.run(client.batch_geocode(["Av T-63"]))

    assert len(res.results) == 1
    assert res.results[0].data.address == "Av T-63"
    assert mock_httpx.request.call_count == 2


def test_batch_reverse_geocode():
    """Testa busca reversa em lote com tuplas de coordenadas."""
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "query": {"latitude": -16.68, "longitude": -49.25},
                "source": "cache",
                "data": {"display_name": "Praça Cívica"},
            }
        ]
    }

    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    res = asyncio.run(client.batch_reverse_geocode([(-16.68, -49.25)]))

    assert len(res.results) == 1
    assert res.results[0].source == "cache"
    assert res.results[0].data["display_name"] == "Praça Cívica"


if __name__ == "__main__":
    print("Iniciando suíte de testes do geocoding-client...")
    test_client_init_and_env()
    print("[PASS] test_client_init_and_env")
    test_client_header_injection()
    print("[PASS] test_client_header_injection")
    test_exception_mapping_401()
    print("[PASS] test_exception_mapping_401")
    test_exception_mapping_404()
    print("[PASS] test_exception_mapping_404")
    test_batch_geocode_and_backoff_retry()
    print("[PASS] test_batch_geocode_and_backoff_retry")
    test_batch_reverse_geocode()
    print("[PASS] test_batch_reverse_geocode")
    print("Todos os testes do cliente passaram com sucesso!")
