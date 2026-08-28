from typing import Any


class GeoAPIError(Exception):
    """Exceção base para todos os erros da API de Geocodificação."""

    def __init__(self, message: str, status_code: int | None = None, response_data: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(GeoAPIError):
    """Lançada quando a chave de API (X-API-Key) é inválida ou ausente (HTTP 401)."""

    pass


class AddressNotFound(GeoAPIError):
    """Lançada quando um endereço ou coordenada não é encontrada (HTTP 404)."""

    pass


class RateLimitExceeded(GeoAPIError):
    """Lançada quando o limite de requisições por minuto é excedido (HTTP 429)."""

    def __init__(
        self,
        message: str = "Limite de requisições excedido na API de geocodificação.",
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class ServerError(GeoAPIError):
    """Lançada quando a API interna ou o servidor Nominatim estão indisponíveis (HTTP 500, 502, 503)."""

    pass


class HTTPConnectionError(GeoAPIError):
    """Lançada quando ocorre uma falha física de conexão de rede ou timeout."""

    pass
