from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GeocodingData(BaseModel):
    """Dados de geocodificação retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    place_id: str = Field(..., description="ID único do local no Nominatim")
    address: str = Field(..., description="Endereço original consultado")
    latitude: float = Field(..., description="Latitude da coordenada")
    longitude: float = Field(..., description="Longitude da coordenada")
    formatted_address: str = Field(..., description="Endereço formatado completo")


class GeocodingResponse(BaseModel):
    """Resposta de busca de endereço por geocodificação direta."""

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado: 'cache', 'nominatim' ou 'error'")
    data: GeocodingData = Field(..., description="Dados detalhados da localização")


class BatchGeocodingRequest(BaseModel):
    """Payload de requisição em lote para geocodificação direta."""

    model_config = ConfigDict(from_attributes=True)

    addresses: list[str] = Field(..., description="Lista de endereços a serem geocodificados")


class BatchGeocodingResponse(BaseModel):
    """Resposta em lote para geocodificação direta."""

    model_config = ConfigDict(from_attributes=True)

    results: list[GeocodingResponse] = Field(..., description="Resultados mantendo a ordem original da busca")


class CoordinateRequest(BaseModel):
    """Coordenada geográfica para consulta."""

    model_config = ConfigDict(from_attributes=True)

    latitude: float = Field(..., description="Latitude da coordenada (-90 a 90)", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude da coordenada (-180 a 180)", ge=-180.0, le=180.0)


class ReverseGeocodingResponse(BaseModel):
    """Resposta de geocodificação reversa."""

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado: 'cache' ou 'nominatim'")
    data: dict[str, Any] = Field(..., description="Dados brutos de endereço retornados pelo Nominatim")


class BatchReverseGeocodingRequest(BaseModel):
    """Payload de requisição em lote para geocodificação reversa."""

    model_config = ConfigDict(from_attributes=True)

    coordinates: list[CoordinateRequest] = Field(..., description="Lista de coordenadas para busca em lote")


class ReverseGeocodingResult(BaseModel):
    """Resultado individual de um item na geocodificação reversa em lote."""

    model_config = ConfigDict(from_attributes=True)

    query: CoordinateRequest = Field(..., description="Coordenada original da consulta")
    source: str = Field(..., description="Origem ('cache', 'nominatim' ou 'error')")
    data: dict[str, Any] | None = Field(default=None, description="Dados brutos de endereço")


class BatchReverseGeocodingResponse(BaseModel):
    """Resposta em lote para geocodificação reversa."""

    model_config = ConfigDict(from_attributes=True)

    results: list[ReverseGeocodingResult] = Field(..., description="Resultados ordenados da consulta em lote")


class HealthResponse(BaseModel):
    """Status de saúde da API de Geocodificação."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Status ('online', 'degraded', 'offline')")
    message: str = Field(..., description="Mensagem descritiva")
    database: bool = Field(..., description="Status do PostgreSQL")
    nominatim: bool = Field(..., description="Status do Nominatim")
