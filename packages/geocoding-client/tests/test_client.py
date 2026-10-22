"""Testes unitários para a classe GeocodingClient (client.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from geocoding_client import (
    AddressNotFound,
    AuthenticationError,
    CoordinateRequest,
    GeoAPIError,
    GeocodingClient,
    HTTPConnectionError,
    RateLimitExceeded,
    ServerError,
)
from geocoding_client.config import ClientSettings

VALID_KEY = "test_secret_key"


def test_client_init_and_env():
    """Testa inicialização do cliente com valores customizados e defaults."""
    client = GeocodingClient(base_url="http://api.test:8000/", api_key="minha_chave")
    assert client.base_url == "http://api.test:8000"
    assert client.api_key == "minha_chave"
    assert client._headers["X-API-Key"] == "minha_chave"


@pytest.mark.anyio
async def test_client_context_manager():
    """Testa o contexto assíncrono (__aenter__ e __aexit__)."""
    mock_httpx = AsyncMock()
    mock_httpx.is_closed = False
    mock_httpx.aclose = AsyncMock()

    client = GeocodingClient(api_key=VALID_KEY)
    client._http_client = mock_httpx

    async with client as c:
        assert c is client

    mock_httpx.aclose.assert_called_once()


@pytest.mark.anyio
async def test_client_close_external_client():
    """Garante que fechar o cliente não encerra um httpx.AsyncClient fornecido externamente."""
    mock_external = AsyncMock()
    mock_external.is_closed = False
    mock_external.aclose = AsyncMock()

    client = GeocodingClient(http_client=mock_external)
    await client.close()

    mock_external.aclose.assert_not_called()


@pytest.mark.anyio
async def test_client_close_internal_client():
    """Garante fechamento correto da sessão quando criado internamente."""
    client = GeocodingClient()
    assert not client._http_client.is_closed
    await client.close()
    assert client._http_client.is_closed


@pytest.mark.anyio
async def test_client_header_injection():
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
    result = await client.geocode("Rua 1")

    assert result.source == "cache"
    assert result.data is not None
    assert result.data.latitude == -16.68
    assert mock_httpx.request.call_count == 1


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (401, AuthenticationError),
        (404, AddressNotFound),
        (500, ServerError),
        (502, ServerError),
        (503, ServerError),
        (504, ServerError),
        (400, GeoAPIError),
    ],
)
def test_handle_response_error_status_codes(
    status_code: int, expected_exception: type[Exception]
):
    """Testa mapeamento dos códigos de status HTTP para exceções tipadas."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"detail": f"Erro simulado {status_code}"}

    client = GeocodingClient()
    with pytest.raises(expected_exception) as exc_info:
        client._handle_response_error(mock_resp)

    assert exc_info.value.status_code == status_code


def test_handle_response_error_non_json():
    """Testa tratamento de erro quando o corpo da resposta não é JSON válido."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 502
    mock_resp.json.side_effect = ValueError("Corpo não é JSON")
    mock_resp.text = "Bad Gateway"

    client = GeocodingClient()
    with pytest.raises(ServerError) as exc_info:
        client._handle_response_error(mock_resp)

    assert "Bad Gateway" in str(exc_info.value)


def test_handle_response_error_rate_limit_with_header():
    """Testa extração do cabeçalho Retry-After em RateLimitExceeded (429)."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "12.5"}
    mock_resp.json.return_value = {"detail": "Rate limit"}

    client = GeocodingClient()
    with pytest.raises(RateLimitExceeded) as exc_info:
        client._handle_response_error(mock_resp)

    assert exc_info.value.retry_after == 12.5


@pytest.mark.anyio
async def test_request_with_backoff_connection_error():
    """Testa lançamento de HTTPConnectionError quando httpx.RequestError ocorre."""
    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(side_effect=httpx.ConnectError("Falha de conexão"))

    settings = ClientSettings(max_retries=1, backoff_factor=0.01)
    client = GeocodingClient(settings=settings, http_client=mock_httpx)

    with pytest.raises(HTTPConnectionError) as exc_info:
        await client._request_with_backoff("GET", "/test")

    assert "Erro de conexão HTTP" in str(exc_info.value)


@pytest.mark.anyio
async def test_health_check_success():
    """Testa chamada ao endpoint /health com retorno 200."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "online",
        "message": "Operacional",
        "database": True,
        "nominatim": True,
    }

    mock_httpx = AsyncMock()
    mock_httpx.get = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    health = await client.health_check()

    assert health.status == "online"
    assert health.database is True


@pytest.mark.anyio
async def test_health_check_degraded_503():
    """Testa chamada ao endpoint /health com retorno 503 (degraded)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.json.return_value = {
        "status": "degraded",
        "message": "Banco indisponível",
        "database": False,
        "nominatim": True,
    }

    mock_httpx = AsyncMock()
    mock_httpx.get = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    health = await client.health_check()

    assert health.status == "degraded"
    assert health.database is False


@pytest.mark.anyio
async def test_batch_geocode_and_backoff_retry():
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
    mock_httpx.request = AsyncMock(side_effect=[resp_429, resp_200])

    client = GeocodingClient(http_client=mock_httpx)
    client.settings.backoff_factor = 0.01

    res = await client.batch_geocode(["Av T-63"])

    assert len(res.results) == 1
    assert res.results[0].data is not None
    assert res.results[0].data.address == "Av T-63"
    assert mock_httpx.request.call_count == 2


@pytest.mark.anyio
async def test_batch_geocode_empty():
    """Testa que passar lista vazia para batch_geocode retorna imediatamente sem requisição."""
    mock_httpx = AsyncMock()
    client = GeocodingClient(http_client=mock_httpx)

    res = await client.batch_geocode([])
    assert len(res.results) == 0
    mock_httpx.request.assert_not_called()


@pytest.mark.anyio
async def test_batch_geocode_chunk_failure_fallback():
    """Garante que falha em um sub-lote gera entradas de erro sem quebrar a execução."""
    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(side_effect=RuntimeError("Falha irrecuperável"))

    client = GeocodingClient(http_client=mock_httpx)
    res = await client.batch_geocode(["Endereço 1", "Endereço 2"])

    assert len(res.results) == 2
    assert res.results[0].source == "error"
    assert res.results[0].data is None


@pytest.mark.anyio
async def test_reverse_geocode():
    """Testa geocodificação reversa individual."""
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "source": "cache",
        "data": {"road": "Av Goiás", "city": "Goiânia"},
    }

    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(return_value=mock_resp)

    client = GeocodingClient(http_client=mock_httpx)
    res = await client.reverse_geocode(-16.68, -49.25)

    assert res.source == "cache"
    assert res.data == {"road": "Av Goiás", "city": "Goiânia"}


@pytest.mark.anyio
async def test_batch_reverse_geocode_chunking_and_types():
    """Testa busca reversa em lote com CoordinateRequest e tuplas, e chunking."""
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
    coords = [CoordinateRequest(latitude=-16.68, longitude=-49.25), (-16.70, -49.26)]
    res = await client.batch_reverse_geocode(coords)

    assert len(res.results) == 1
    assert res.results[0].source == "cache"


@pytest.mark.anyio
async def test_batch_reverse_geocode_empty():
    """Testa lista vazia para batch_reverse_geocode."""
    mock_httpx = AsyncMock()
    client = GeocodingClient(http_client=mock_httpx)

    res = await client.batch_reverse_geocode([])
    assert len(res.results) == 0
    mock_httpx.request.assert_not_called()


@pytest.mark.anyio
async def test_batch_reverse_geocode_failure_fallback():
    """Garante fallback para source='error' em falha no sub-lote reverso."""
    mock_httpx = AsyncMock()
    mock_httpx.request = AsyncMock(side_effect=RuntimeError("Falha de rede"))

    client = GeocodingClient(http_client=mock_httpx)
    res = await client.batch_reverse_geocode([(-16.68, -49.25)])

    assert len(res.results) == 1
    assert res.results[0].source == "error"
    assert res.results[0].data is None


def test_sync_methods_wrappers():
    """Valida os métodos auxiliares síncronos (*_sync)."""
    client = GeocodingClient()

    with patch.object(client, "geocode") as mock_geocode:
        mock_geocode.return_value = MagicMock()
        client.geocode_sync("Rua Teste")
        mock_geocode.assert_called_once_with("Rua Teste")

    with patch.object(client, "batch_geocode") as mock_batch_geo:
        mock_batch_geo.return_value = MagicMock()
        client.batch_geocode_sync(["Rua 1"])
        mock_batch_geo.assert_called_once_with(["Rua 1"])

    with patch.object(client, "reverse_geocode") as mock_rev:
        mock_rev.return_value = MagicMock()
        client.reverse_geocode_sync(-16.68, -49.25)
        mock_rev.assert_called_once_with(-16.68, -49.25)

    with patch.object(client, "batch_reverse_geocode") as mock_batch_rev:
        mock_batch_rev.return_value = MagicMock()
        client.batch_reverse_geocode_sync([(-16.68, -49.25)])
        mock_batch_rev.assert_called_once_with([(-16.68, -49.25)])
