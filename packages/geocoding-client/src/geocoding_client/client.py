import asyncio
from typing import Any, Self

import httpx
from logging_settings import setup_logger
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

logger = setup_logger(__name__)


class GeocodingClient:
    """Cliente HTTP assíncrono para consumo da API interna de Geocodificação.

    Fornece interface para geocodificação direta, reversa e operações em lote (batch),
    com suporte nativo a autenticação M2M via cabeçalho `X-API-Key` e resiliência
    a limites de taxa (Rate Limit) através de Exponential Backoff.

    Attributes:
        settings (ClientSettings): Instância de configurações do cliente.
        base_url (str): URL base da API de Geocodificação.
        api_key (str): Chave de autenticação M2M utilizada nas requisições.

    Example:
        >>> async with GeocodingClient() as client:
        ...     res = await client.geocode("Avenida Anhanguera, Goiânia")
        ...     print(res.data.latitude, res.data.longitude)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        settings: ClientSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Inicializa a instância do GeocodingClient.

        Args:
            base_url (str | None): URL base da API (ex: 'http://localhost:8000').
                Se omitido, utiliza o valor da variável de ambiente GEO_API_URL.
            api_key (str | None): Chave M2M enviada no cabeçalho X-API-Key.
                Se omitido, utiliza o valor da variável de ambiente GEO_API_KEY.
            settings (ClientSettings | None): Instância customizada de configurações.
            http_client (httpx.AsyncClient | None): Cliente HTTP assíncrono customizado.
                Caso seja fornecido, o ciclo de vida do cliente será mantido externamente.
        """
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
        """Entra no contexto assíncrono do cliente."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Encerra o contexto assíncrono fechando as conexões HTTP."""
        await self.close()

    async def close(self) -> None:
        """Encerra a sessão do cliente HTTP assíncrono interno.

        Se o cliente HTTP foi fornecido externamente na inicialização, esta função
        não encerrará a sessão externa.
        """
        if not self._external_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Mapeia os códigos de status HTTP de erro para exceções fortemente tipadas.

        Args:
            response (httpx.Response): Objeto de resposta HTTP retornado pelo servidor.

        Raises:
            AuthenticationError: Se o código de status for 401 (API Key inválida/ausente).
            AddressNotFound: Se o código de status for 404 (Endereço não localizado).
            RateLimitExceeded: Se o código de status for 429 (Limite de requisições excedido).
            ServerError: Se o código de status for 500, 502, 503 ou 504.
            GeoAPIError: Para qualquer outro status HTTP de erro não específico.
        """
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
        """Executa uma requisição HTTP aplicando Exponential Backoff com jitter.

        Apenas exceções temporárias (RateLimitExceeded, ServerError, HTTPConnectionError)
        são retentadas até o limite estipulado em `self.settings.max_retries`.

        Args:
            method (str): Método HTTP ('GET', 'POST', etc.).
            url (str): Endpoint relativo ou URL de destino.
            **kwargs (Any): Argumentos adicionais repassados para `httpx.AsyncClient.request`.

        Returns:
            httpx.Response: Resposta HTTP de sucesso (status 2xx).

        Raises:
            RateLimitExceeded: Se o limite de retentativas for atingido sob 429.
            ServerError: Se o servidor persistir em erro 5xx após as retentativas.
            HTTPConnectionError: Se a conexão física falhar consecutivamente.
        """
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
                        f"Falha de conexão com a API de Geocodificação: {exc}. "
                        f"Tentativa {attempt.retry_state.attempt_number} de {self.settings.max_retries}"
                    )

                    raise HTTPConnectionError(f"Erro de conexão HTTP: {exc}") from exc

                except (RateLimitExceeded, ServerError) as exc:
                    logger.warning(
                        f"Requisição falhou com status temporário ({exc.status_code}): {exc.message}. "
                        f"Tentativa {attempt.retry_state.attempt_number} de {self.settings.max_retries}"
                    )

                    raise

        raise GeoAPIError("Falha inesperada no fluxo de retentativa.")

    # -------------------------------------------------------------------------
    # Métodos Assíncronos da API Pública
    # -------------------------------------------------------------------------

    async def health_check(self) -> HealthResponse:
        """Consulta o endpoint de saúde e diagnóstico ativo da API de Geocodificação.

        Returns:
            HealthResponse: Objeto contendo o status global ('online', 'degraded', 'offline')
                e os diagnósticos individuais da base PostgreSQL e do servidor Nominatim.

        Raises:
            GeoAPIError: Caso a resposta da API não seja um JSON válido de diagnóstico.
        """
        response = await self._http_client.get("/health")

        if response.status_code not in (200, 503):
            self._handle_response_error(response)

        return HealthResponse.model_validate(response.json())

    async def geocode(self, address: str) -> GeocodingResponse:
        """Converte um endereço textual completo em coordenadas geográficas (Latitude e Longitude).

        Args:
            address (str): Endereço residencial ou comercial completo.

        Returns:
            GeocodingResponse: Dados com coordenadas, endereço formatado e origem do resultado ('cache' ou 'nominatim').

        Raises:
            AuthenticationError: Se a API Key fornecida for inválida (HTTP 401).
            AddressNotFound: Se o endereço não for localizado (HTTP 404).
            RateLimitExceeded: Se o limite de taxa for ultrapassado e as retentativas esgotarem (HTTP 429).
            ServerError: Se a API interna ou o Nominatim falharem (HTTP 5xx).

        Example:
            >>> result = await client.geocode("Avenida Anhanguera, Goiânia")
            >>> print(result.data.latitude, result.data.longitude)
        """
        response = await self._request_with_backoff("GET", "/geocoding/search", params={"address": address})

        return GeocodingResponse.model_validate(response.json())

    async def batch_geocode(self, addresses: list[str]) -> BatchGeocodingResponse:
        """Geocodifica múltiplos endereços em lote fracionando automaticamente em sub-lotes de no máximo 100 itens.

        Aplica retentativa automática com Exponential Backoff para garantir que as requisições
        em lote não falhem devido a limitações temporárias de taxa.

        Args:
            addresses (list[str]): Lista contendo os endereços a serem geocodificados.

        Returns:
            BatchGeocodingResponse: Resposta em lote mantendo a mesma ordem original da lista.

        Raises:
            AuthenticationError: Se a API Key for inválida (HTTP 401).
            RateLimitExceeded: Se o limite de requisições em lote for excedido (HTTP 429).
            ServerError: Se ocorrer erro na API ou infraestrutura (HTTP 5xx).
        """
        if not addresses:
            return BatchGeocodingResponse(results=[])

        batch_size = 100
        all_results = []

        for i in range(0, len(addresses), batch_size):
            chunk = addresses[i : i + batch_size]
            payload = BatchGeocodingRequest(addresses=chunk).model_dump()
            try:
                response = await self._request_with_backoff("POST", "/geocoding/search/batch", json=payload)
                sub_batch = BatchGeocodingResponse.model_validate(response.json())
                all_results.extend(sub_batch.results)
            except Exception as exc:
                logger.warning(f"Falha no sub-lote de geocodificação ({i} a {i + len(chunk)}): {exc}")
                empty_results = [
                    GeocodingResponse(
                        source="error",
                        data=None,
                    )
                    for _ in chunk
                ]
                all_results.extend(empty_results)

        return BatchGeocodingResponse(results=all_results)

    async def reverse_geocode(self, latitude: float, longitude: float) -> ReverseGeocodingResponse:
        """Realiza a geocodificação reversa, convertendo Latitude e Longitude em endereço completo.

        Args:
            latitude (float): Latitude da coordenada (-90.0 a 90.0).
            longitude (float): Longitude da coordenada (-180.0 a 180.0).

        Returns:
            ReverseGeocodingResponse: Dados do endereço encontrado e atributos detalhados.

        Raises:
            AuthenticationError: Se a API Key for inválida (HTTP 401).
            AddressNotFound: Se nenhum endereço for localizado para o ponto informado (HTTP 404).
            RateLimitExceeded: Se o limite de requisições for excedido (HTTP 429).
        """
        params = {"lat": latitude, "lon": longitude}
        response = await self._request_with_backoff("GET", "/geocoding/reverse", params=params)

        return ReverseGeocodingResponse.model_validate(response.json())

    async def batch_reverse_geocode(
        self, coordinates: list[CoordinateRequest | tuple[float, float]]
    ) -> BatchReverseGeocodingResponse:
        """Realiza a geocodificação reversa em lote fracionando em sub-lotes de no máximo 100 itens.

        Args:
            coordinates (list[CoordinateRequest | tuple[float, float]]): Lista de objetos
                CoordinateRequest ou tuplas `(latitude, longitude)`.

        Returns:
            BatchReverseGeocodingResponse: Lista de resultados na ordem exata solicitada.

        Raises:
            AuthenticationError: Se a API Key for inválida (HTTP 401).
            RateLimitExceeded: Se o limite de requisições for excedido (HTTP 429).
        """
        if not coordinates:
            return BatchReverseGeocodingResponse(results=[])

        coord_objects = [
            c if isinstance(c, CoordinateRequest) else CoordinateRequest(latitude=c[0], longitude=c[1])
            for c in coordinates
        ]

        batch_size = 100
        all_results = []

        for i in range(0, len(coord_objects), batch_size):
            chunk = coord_objects[i : i + batch_size]
            payload = BatchReverseGeocodingRequest(coordinates=chunk).model_dump()
            try:
                response = await self._request_with_backoff("POST", "/geocoding/reverse/batch", json=payload)
                sub_batch = BatchReverseGeocodingResponse.model_validate(response.json())
                all_results.extend(sub_batch.results)
            except Exception as exc:
                logger.warning(f"Falha no sub-lote de geocodificação reversa ({i} a {i + len(chunk)}): {exc}")
                empty_results = [
                    ReverseGeocodingResponse(
                        source="error",
                        data=None,
                    )
                    for _ in chunk
                ]
                all_results.extend(empty_results)

        return BatchReverseGeocodingResponse(results=all_results)

    # -------------------------------------------------------------------------
    # Métodos Síncronos Facilitadores
    # -------------------------------------------------------------------------

    def geocode_sync(self, address: str) -> GeocodingResponse:
        """Versão síncrona do método `geocode`.

        Args:
            address (str): Endereço completo para busca.

        Returns:
            GeocodingResponse: Dados de geocodificação direta.
        """
        return asyncio.run(self.geocode(address))

    def batch_geocode_sync(self, addresses: list[str]) -> BatchGeocodingResponse:
        """Versão síncrona do método `batch_geocode`.

        Args:
            addresses (list[str]): Lista de endereços.

        Returns:
            BatchGeocodingResponse: Resultados em lote.
        """
        return asyncio.run(self.batch_geocode(addresses))

    def reverse_geocode_sync(self, latitude: float, longitude: float) -> ReverseGeocodingResponse:
        """Versão síncrona do método `reverse_geocode`.

        Args:
            latitude (float): Latitude.
            longitude (float): Longitude.

        Returns:
            ReverseGeocodingResponse: Endereço retornado.
        """
        return asyncio.run(self.reverse_geocode(latitude, longitude))

    def batch_reverse_geocode_sync(
        self, coordinates: list[CoordinateRequest | tuple[float, float]]
    ) -> BatchReverseGeocodingResponse:
        """Versão síncrona do método `batch_reverse_geocode`.

        Args:
            coordinates (list[CoordinateRequest | tuple[float, float]]): Lista de coordenadas.

        Returns:
            BatchReverseGeocodingResponse: Resultados ordenados.
        """
        return asyncio.run(self.batch_reverse_geocode(coordinates))
