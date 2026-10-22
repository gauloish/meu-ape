"""Testes unitários para exceções customizadas do geocoding-client (exceptions.py)."""

from geocoding_client.exceptions import (
    AddressNotFound,
    AuthenticationError,
    GeoAPIError,
    HTTPConnectionError,
    RateLimitExceeded,
    ServerError,
)


def test_geo_api_error_representation():
    """Valida representação textual de GeoAPIError com e sem status_code."""
    err_with_code = GeoAPIError("Erro de teste", status_code=400)
    assert str(err_with_code) == "[400] Erro de teste"
    assert err_with_code.status_code == 400

    err_without_code = GeoAPIError("Falha genérica")
    assert str(err_without_code) == "Falha genérica"
    assert err_without_code.status_code is None


def test_custom_exception_subclasses():
    """Valida que todas as exceções especializadas herdam de GeoAPIError."""
    assert issubclass(AuthenticationError, GeoAPIError)
    assert issubclass(AddressNotFound, GeoAPIError)
    assert issubclass(RateLimitExceeded, GeoAPIError)
    assert issubclass(ServerError, GeoAPIError)
    assert issubclass(HTTPConnectionError, GeoAPIError)


def test_rate_limit_exceeded_retry_after():
    """Valida atributo retry_after em RateLimitExceeded."""
    exc = RateLimitExceeded(
        message="Muitas requisições",
        retry_after=30.0,
        response_data={"error": "rate_limit"},
    )
    assert exc.status_code == 429
    assert exc.retry_after == 30.0
    assert exc.response_data == {"error": "rate_limit"}
    assert "[429]" in str(exc)
