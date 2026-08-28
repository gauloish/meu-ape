from .client import GeocodingClient
from .config import ClientSettings, settings
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
    GeocodingData,
    GeocodingResponse,
    HealthResponse,
    ReverseGeocodingResponse,
    ReverseGeocodingResult,
)

__all__ = [
    # Client
    "GeocodingClient",
    # Config
    "ClientSettings",
    "settings",
    # Exceptions
    "GeoAPIError",
    "AuthenticationError",
    "AddressNotFound",
    "RateLimitExceeded",
    "ServerError",
    "HTTPConnectionError",
    # Schemas
    "GeocodingData",
    "GeocodingResponse",
    "BatchGeocodingRequest",
    "BatchGeocodingResponse",
    "CoordinateRequest",
    "ReverseGeocodingResponse",
    "BatchReverseGeocodingRequest",
    "ReverseGeocodingResult",
    "BatchReverseGeocodingResponse",
    "HealthResponse",
]
