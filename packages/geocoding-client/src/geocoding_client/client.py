import asyncio
import logging
from typing import Any, Self

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import ClientSettings, settings as default_settings
from .exceptions import (
    AddressNotFound,
    AuthenticationError,
    GeoAPIError,
    HTTPConnectionError,
    RateLimitExceeded,
    ServerError,
)
from .schemas import (
    BatchGeocodingRequest,
    BatchGeocodingResponse,
    BatchReverseGeocodingRequest,
    BatchReverseGeocodingResponse,
    CoordinateRequest,
    GeocodingResponse,
    HealthResponse,
    ReverseGeocodingResponse,
)

logger = logging.getLogger(__name__)


class GeocodingClient:
    """Cliente assíncrono moderno para consumo da API interna de Geocodificação."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        settings: ClientSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Inicializa o cliente com parâmetros customizados ou variáveis de ambiente (GEO_API_URL, GEO_API_KEY)."""
        self.settings = settings or default_settings
        self.base_url = (base_url or self.settings.geo_api_url).rstrip("/")
        self.api_key = api_key or self.settings.geo_api_key

        self._headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self._external_client = http_client is not None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=httpx.Timeout(self.settings.timeout),
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Encerra a sessão do cliente HTTP se ela tiver sido criada internamente."""
        if not self._external_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Mapeia códigos de erro HTTP para exceções fortemente tipadas."""
        if response.is_success:
            return

        status_code = response.status_code
        try:
            body = response.json()
            message = body.get("detail", response.text)
        except Exception:
            body = None
            message = response.text or f"Erro HTTP {status_code}"

        if status_code == 401:
            raise AuthenticationError(message, status_code=status_code, response_data=body)
        elif status_code == 404:
            raise AddressNotFound(message, status_code=status_code, response_data=body)
        elif status_code == 429:
            retry_after_str = response.headers.get("Retry-After")
            retry_after = float(retry_after_str) if retry_after_str else None
            raise RateLimitExceeded(message, retry_after=retry_after, response_data=body)
        elif status_code in (500, 502, 503, 504):
            raise ServerError(message, status_code=status_code, response_data=body)
        else:
            raise GeoAPIError(message, status_code=status_code, response_data=body)

    async def _request_with_backoff(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Executa a requisição HTTP aplicando Exponential Backoff em caso de RateLimit ou indisponibilidade temporária."""
        retrier = AsyncRetrying(
            stop=stop_after_attempt(self.settings.max_retries),
            wait=wait_exponential_jitter(initial=self.settings.backoff_factor, max=30.0),
            retry=retry_if_exception_type((RateLimitExceeded, ServerError, HTTPConnectionError)),
            reraise=True,
        )

        async for attempt in retrier:
            with attempt:
                try:
                    response = await self._http_client.request(method, url, **kwargs)
                    self._handle_response_error(response)
                    return response
                except httpx.RequestError as exc:
                    logger.warning(
                        f"Falha de conexão com a API de Geocodificação: {exc}. Tentativa {attempt.retry_state.attempt_number} de {self.settings.max_retries}"
                    )
                    raise HTTPConnectionError(f"Erro de conexão HTTP: {exc}") from exc
                except (RateLimitExceeded, ServerError) as exc:
                    logger.warning(
                        f"Requisição falhou com status temporário ({exc.status_code}): {exc.message}. Tentativa {attempt.retry_state.attempt_number} de {self.settings.max_retries}"
                    )
                    raise

        raise GeoAPIError("Falha inesperada no fluxo de retentativa.")

    # -------------------------------------------------------------------------
    # Métodos Assíncronos da API Pública
    # -------------------------------------------------------------------------

    async def health_check(self) -> HealthResponse:
        """Verifica o status de saúde da API e suas dependências."""
        response = await self._http_client.get("/health")
        if response.status_code not in (200, 503):
            self._handle_response_error(response)
        return HealthResponse.model_validate(response.json())

    async def geocode(self, address: str) -> GeocodingResponse:
        """Converte um endereço completo em coordenadas geográficas.

        Args:
            address: Endereço completo para geocodificação.

        Returns:
            GeocodingResponse: Coordenadas e dados de endereço.
        """
        response = await self._request_with_backoff("GET", "/geocoding/search", params={"address": address})
        return GeocodingResponse.model_validate(response.json())

    async def batch_geocode(self, addresses: list[str]) -> BatchGeocodingResponse:
        """Geocodifica múltiplos endereços em lote com resiliência a Rate Limit.

        Args:
            addresses: Lista de strings com os endereços.

        Returns:
            BatchGeocodingResponse: Lista de resultados na mesma ordem da requisição.
        """
        payload = BatchGeocodingRequest(addresses=addresses).model_dump()
        response = await self._request_with_backoff("POST", "/geocoding/search/batch", json=payload)
        return BatchGeocodingResponse.model_validate(response.json())

    async def reverse_geocode(self, latitude: float, longitude: float) -> ReverseGeocodingResponse:
        """Converte coordenadas geográficas (Latitude e Longitude) em endereço.

        Args:
            latitude: Latitude (-90 a 90).
            longitude: Longitude (-180 a 180).

        Returns:
            ReverseGeocodingResponse: Dados do endereço encontrado.
        """
        params = {"lat": latitude, "lon": longitude}
        response = await self._request_with_backoff("GET", "/geocoding/reverse", params=params)
        return ReverseGeocodingResponse.model_validate(response.json())

    async def batch_reverse_geocode(
        self, coordinates: list[CoordinateRequest | tuple[float, float]]
    ) -> BatchReverseGeocodingResponse:
        """Geocodifica múltiplas coordenadas geográficas em lote.

        Args:
            coordinates: Lista de objetos CoordinateRequest ou tuplas (latitude, longitude).

        Returns:
            BatchReverseGeocodingResponse: Resultados ordenados.
        """
        coord_objects = [
            c if isinstance(c, CoordinateRequest) else CoordinateRequest(latitude=c[0], longitude=c[1])
            for c in coordinates
        ]
        payload = BatchReverseGeocodingRequest(coordinates=coord_objects).model_dump()
        response = await self._request_with_backoff("POST", "/geocoding/reverse/batch", json=payload)
        return BatchReverseGeocodingResponse.model_validate(response.json())

    # -------------------------------------------------------------------------
    # Métodos Síncronos Facilitadores
    # -------------------------------------------------------------------------

    def geocode_sync(self, address: str) -> GeocodingResponse:
        """Versão síncrona de geocode."""
        return asyncio.run(self.geocode(address))

    def batch_geocode_sync(self, addresses: list[str]) -> BatchGeocodingResponse:
        """Versão síncrona de batch_geocode."""
        return asyncio.run(self.batch_geocode(addresses))

    def reverse_geocode_sync(self, latitude: float, longitude: float) -> ReverseGeocodingResponse:
        """Versão síncrona de reverse_geocode."""
        return asyncio.run(self.reverse_geocode(latitude, longitude))

    def batch_reverse_geocode_sync(
        self, coordinates: list[CoordinateRequest | tuple[float, float]]
    ) -> BatchReverseGeocodingResponse:
        """Versão síncrona de batch_reverse_geocode."""
        return asyncio.run(self.batch_reverse_geocode(coordinates))
