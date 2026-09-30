"""Pacote cliente Python para consumo da API de Geocodificação (`geocoding-client`).

Fornece cliente assíncrono e síncrono com suporte nativo a requisições individuais e em lote,
autenticação M2M via cabeçalho `X-API-Key`, e resiliência via Exponential Backoff.
"""

from src.client import GeocodingClient
from src.config import ClientSettings, settings
from src.exceptions import (
    AddressNotFound,
    AuthenticationError,
    GeoAPIError,
    HTTPConnectionError,
    RateLimitExceeded,
    ServerError,
)
from src.schemas import (
    BatchGeocodingRequest,
    BatchGeocodingResponse,
    BatchReverseGeocodingRequest,
    BatchReverseGeocodingResponse,
    CoordinateRequest,
    GeocodingData,
    GeocodingResponse,
    HealthResponse,
    ReverseGeocodingResponse,
    ReverseGeocodingResult,
)

__all__ = [
    "AddressNotFound",
    "AuthenticationError",
    "BatchGeocodingRequest",
    "BatchGeocodingResponse",
    "BatchReverseGeocodingRequest",
    "BatchReverseGeocodingResponse",
    "ClientSettings",
    "CoordinateRequest",
    "GeoAPIError",
    "GeocodingClient",
    "GeocodingData",
    "GeocodingResponse",
    "HTTPConnectionError",
    "HealthResponse",
    "RateLimitExceeded",
    "ReverseGeocodingResponse",
    "ReverseGeocodingResult",
    "ServerError",
    "settings",
]
