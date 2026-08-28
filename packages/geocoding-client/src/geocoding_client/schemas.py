"""Modelos de dados (DTOs) para o cliente de Geocodificação.

Define os esquemas Pydantic V2 utilizados na serialização, validação e desserialização
das requisições e respostas trocadas com a API interna de Geocodificação.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GeocodingData(BaseModel):
    """Atributos detalhados do resultado de geocodificação direta.

    Attributes:
        place_id (str): Identificador único do local no servidor Nominatim.
        address (str): Endereço de busca original submetido na requisição.
        latitude (float): Latitude geográfica da localização.
        longitude (float): Longitude geográfica da localização.
        formatted_address (str): Endereço formatado e padronizado retornado pela API.
    """

    model_config = ConfigDict(from_attributes=True)

    place_id: str = Field(..., description="ID único do local no Nominatim")
    address: str = Field(..., description="Endereço original consultado")
    latitude: float = Field(..., description="Latitude da coordenada")
    longitude: float = Field(..., description="Longitude da coordenada")
    formatted_address: str = Field(..., description="Endereço formatado completo")


class GeocodingResponse(BaseModel):
    """Objeto de resposta para consulta de geocodificação direta individual.

    Attributes:
        source (str): Origem da informação ('cache', 'nominatim' ou 'error').
        data (GeocodingData): Dados detalhados de geocodificação.
    """

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado: 'cache', 'nominatim' ou 'error'")
    data: GeocodingData = Field(..., description="Dados detalhados da localização")


class BatchGeocodingRequest(BaseModel):
    """Corpo da requisição para geocodificação direta em lote (batch).

    Attributes:
        addresses (list[str]): Lista com os endereços textuais para consulta.
    """

    model_config = ConfigDict(from_attributes=True)

    addresses: list[str] = Field(..., description="Lista de endereços a serem geocodificados")


class BatchGeocodingResponse(BaseModel):
    """Resposta contendo os resultados da geocodificação direta em lote.

    Attributes:
        results (list[GeocodingResponse]): Lista de respostas correspondentes na mesma ordem solicitada.
    """

    model_config = ConfigDict(from_attributes=True)

    results: list[GeocodingResponse] = Field(..., description="Resultados mantendo a ordem original da busca")


class CoordinateRequest(BaseModel):
    """Representação de uma coordenada geográfica de entrada.

    Attributes:
        latitude (float): Latitude entre -90.0 e 90.0.
        longitude (float): Longitude entre -180.0 e 180.0.
    """

    model_config = ConfigDict(from_attributes=True)

    latitude: float = Field(..., description="Latitude da coordenada (-90 a 90)", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude da coordenada (-180 a 180)", ge=-180.0, le=180.0)


class ReverseGeocodingResponse(BaseModel):
    """Objeto de resposta para consulta de geocodificação reversa individual.

    Attributes:
        source (str): Origem do dado ('cache' ou 'nominatim').
        data (dict[str, Any]): Dicionário com os atributos de endereço retornados pelo Nominatim.
    """

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(..., description="Origem do dado: 'cache' ou 'nominatim'")
    data: dict[str, Any] = Field(..., description="Dados brutos de endereço retornados pelo Nominatim")


class BatchReverseGeocodingRequest(BaseModel):
    """Corpo da requisição para geocodificação reversa em lote (batch).

    Attributes:
        coordinates (list[CoordinateRequest]): Lista de coordenadas a serem consultadas.
    """

    model_config = ConfigDict(from_attributes=True)

    coordinates: list[CoordinateRequest] = Field(..., description="Lista de coordenadas para busca em lote")


class ReverseGeocodingResult(BaseModel):
    """Resultado individual de um item na geocodificação reversa em lote.

    Attributes:
        query (CoordinateRequest): Coordenada original enviada na consulta.
        source (str): Origem do resultado ('cache', 'nominatim' ou 'error').
        data (dict[str, Any] | None): Dicionário com o endereço retornado ou None se não encontrado.
    """

    model_config = ConfigDict(from_attributes=True)

    query: CoordinateRequest = Field(..., description="Coordenada original da consulta")
    source: str = Field(..., description="Origem ('cache', 'nominatim' ou 'error')")
    data: dict[str, Any] | None = Field(default=None, description="Dados brutos de endereço")


class BatchReverseGeocodingResponse(BaseModel):
    """Resposta contendo os resultados da geocodificação reversa em lote.

    Attributes:
        results (list[ReverseGeocodingResult]): Lista de resultados ordenados.
    """

    model_config = ConfigDict(from_attributes=True)

    results: list[ReverseGeocodingResult] = Field(..., description="Resultados ordenados da consulta em lote")


class HealthResponse(BaseModel):
    """Diagnóstico do estado de saúde da API e suas dependências.

    Attributes:
        status (str): Status global da aplicação ('online', 'degraded', 'offline').
        message (str): Descrição informativa do estado da API.
        database (bool): Indicador de conectividade com o banco de dados PostgreSQL.
        nominatim (bool): Indicador de conectividade com o servidor Nominatim.
    """

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="Status ('online', 'degraded', 'offline')")
    message: str = Field(..., description="Mensagem descritiva")
    database: bool = Field(..., description="Status do PostgreSQL")
    nominatim: bool = Field(..., description="Status do Nominatim")
