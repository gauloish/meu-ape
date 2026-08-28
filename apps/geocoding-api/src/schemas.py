from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GeocodingData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    place_id: str = Field(..., description="ID único do local no Nominatim")
    address: str = Field(..., description="Endereço original usado na busca")
    latitude: float = Field(..., description="Latitude da coordenada")
    longitude: float = Field(..., description="Longitude da coordenada")
    formatted_address: str = Field(..., description="Endereço formatado retornado pelo Nominatim")


class GeocodingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado: 'cache' (banco) ou 'nominatim' (API externa)")
    data: GeocodingData


class HealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Status atual da aplicação ('online', 'degraded', 'offline')")
    message: str = Field(..., description="Mensagem detalhada do status")
    database: bool = Field(..., description="Conectividade com banco de dados PostgreSQL")
    nominatim: bool = Field(..., description="Conectividade com servidor Nominatim")


class BatchGeocodingRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    addresses: list[str] = Field(
        ...,
        description="Lista de endereços para busca em lote",
        min_length=1,
        max_length=100,
    )


class BatchGeocodingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    results: list[GeocodingResponse] = Field(..., description="Lista de resultados correspondentes")


class CoordinateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latitude: float = Field(..., description="Latitude", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude", ge=-180.0, le=180.0)


class ReverseGeocodingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado ('cache' ou 'nominatim')")
    data: dict[str, Any] = Field(..., description="Dados do endereço retornado pelo Nominatim")


class BatchReverseGeocodingRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coordinates: list[CoordinateRequest] = Field(
        ...,
        description="Lista de coordenadas para busca em lote",
        min_length=1,
        max_length=100,
    )


class ReverseGeocodingResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: CoordinateRequest = Field(..., description="Coordenada original consultada")
    source: str = Field(..., description="Origem ('cache', 'nominatim' ou 'error')")
    data: dict[str, Any] | None = Field(default=None, description="Dados brutos retornados pelo Nominatim")


class BatchReverseGeocodingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    results: list[ReverseGeocodingResult] = Field(..., description="Resultados do reverse geocoding em lote")
