"""Módulo de exceções customizadas do cliente de Geocodificação.

Define a hierarquia de exceções utilizadas para mapear erros HTTP e falhas
de rede durante o consumo da API interna de Geocodificação.
"""

from typing import Any


class GeoAPIError(Exception):
    """Exceção base para todos os erros gerados pelo cliente de Geocodificação.

    Attributes:
        message (str): Mensagem descritiva da falha.
        status_code (int | None): Código de status HTTP retornado pela API, se aplicável.
        response_data (Any): Corpo da resposta da API (JSON/dict ou texto bruto).
    """

    def __init__(self, message: str, status_code: int | None = None, response_data: Any = None) -> None:
        """Inicializa a exceção GeoAPIError.

        Args:
            message (str): Descrição legível do erro.
            status_code (int | None): Código HTTP retornado pela API.
            response_data (Any): Dados adicionais do corpo da resposta.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
            
        return self.message


class AuthenticationError(GeoAPIError):
    """Lançada quando a chave de API enviada via X-API-Key é inválida ou ausente (HTTP 401)."""

    pass


class AddressNotFound(GeoAPIError):
    """Lançada quando um endereço textual ou coordenada geográfica não é localizada (HTTP 404)."""

    pass


class RateLimitExceeded(GeoAPIError):
    """Lançada quando o limite de requisições por minuto é excedido (HTTP 429).

    Attributes:
        retry_after (float | None): Tempo sugerido em segundos para aguardar antes da próxima tentativa.
    """

    def __init__(
        self,
        message: str = "Limite de requisições excedido na API de geocodificação.",
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Inicializa a exceção de limite de taxa.

        Args:
            message (str): Mensagem descritiva do erro.
            retry_after (float | None): Tempo em segundos até o re-estabelecimento da cota.
            **kwargs (Any): Argumentos adicionais repassados à classe pai GeoAPIError.
        """
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after


class ServerError(GeoAPIError):
    """Lançada quando a API de geocodificação ou o servidor Nominatim reportam erro interno (HTTP 500, 502, 503, 504)."""

    pass


class HTTPConnectionError(GeoAPIError):
    """Lançada quando ocorre uma falha física de rede, timeout ou recusa de conexão."""

    pass
