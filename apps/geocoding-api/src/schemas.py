from typing import List
from pydantic import BaseModel, Field


class GeocodingData(BaseModel):
    place_id: str = Field(..., description="ID único do local no Nominatim")
    address: str = Field(..., description="Endereço original usado na busca")
    latitude: float = Field(..., description="Latitude da coordenada")
    longitude: float = Field(..., description="Longitude da coordenada")
    formatted_address: str = Field(..., description="Endereço formatado e padronizado retornado pelo Nominatim")


class GeocodingResponse(BaseModel):
    source: str = Field(..., description="Origem do dado: 'cache' (banco de dados) ou 'nominatim' (API externa)")
    data: GeocodingData


class HealthResponse(BaseModel):
    status: str = Field(..., description="Status atual da aplicação (ex: online)")
    message: str = Field(..., description="Mensagem descritiva do status")


class BatchGeocodingRequest(BaseModel):
    addresses: List[str] = Field(
        ..., 
        description="Lista de endereços para buscar", 
        max_length=100
    )

class BatchGeocodingResponse(BaseModel):
    results: List[GeocodingResponse] = Field(..., description="Lista com os resultados correspondentes")