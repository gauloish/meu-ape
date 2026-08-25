import os
import asyncio
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.session import get_db
from ..database.repositories import GeocodingRepository
from ..database.models import GeocodingCache
from ..schemas import (
    GeocodingResponse, 
    GeocodingData, 
    BatchGeocodingRequest, 
    BatchGeocodingResponse,
    CoordinateRequest,
    BatchReverseGeocodingRequest, 
    BatchReverseGeocodingResponse,
    ReverseGeocodingResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geocoding", tags=["Geocoding"])


NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://nominatim_server:8080")
USER_AGENT = "GeocodingAPI/1.0"


@router.get(
    "/search",
    response_model=GeocodingResponse, 
    summary="Busca coordenadas por endereço (com cache)"
)
async def search_address(
    address: str = Query(..., description="Endereço completo para buscar"),
    db: AsyncSession = Depends(get_db)
):
    repo = GeocodingRepository(db)

    try:
        cached_address = await repo.get(address)

        if cached_address:
            logger.info(f"Cache HIT para o endereço: '{address}'")

            return GeocodingResponse(
                source="cache",
                data=GeocodingData(
                    place_id=cached_address.place_id,
                    address=cached_address.address,
                    latitude=cached_address.latitude,
                    longitude=cached_address.longitude,
                    formatted_address=cached_address.formatted_address
                )
            )

    except Exception as e:
        logger.error(f"Erro ao consultar o cache: {e}")

    logger.info(f"Cache MISS. Buscando '{address}' no Nominatim...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOMINATIM_URL}/search",
                params={"q": address, "format": "json", "addressdetails": 1, "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0
            )

            response.raise_for_status()
            data = response.json()

            if not data:
                raise HTTPException(status_code=404, detail="Endereço não encontrado no mapa.")

            first_result = data[0]

            new_cache = GeocodingCache(
                address=address,
                latitude=float(first_result["latitude"]),
                longitude=float(first_result["longitude"]),
                formatted_address=first_result["display_name"],
                place_id=str(first_result["place_id"])
            )
            
            try:
                await repo.add(new_cache, auto_commit=True)
                logger.info(f"Novo endereço salvo no cache: '{address}'")

            except Exception as e:
                logger.error(f"Não foi possível salvar no cache: {e}")

            return GeocodingResponse(
                source="nominatim",
                data=GeocodingData(
                    place_id=str(first_result["place_id"]),
                    address=address,
                    latitude=float(first_result["latitude"]),
                    longitude=float(first_result["longitude"]),
                    formatted_address=first_result["display_name"]
                )
            )

        except httpx.RequestError as exc:
            logger.error(f"Erro de conexão com o Nominatim: {exc}")
            raise HTTPException(status_code=502, detail="Serviço de geocodificação indisponível.")


@router.post(
    "/search/batch", 
    response_model=BatchGeocodingResponse, 
    summary="Busca coordenadas para múltiplos endereços em lote (Concorrente)"
)
async def batch_search_address(
    request: BatchGeocodingRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = GeocodingRepository(db)
    final_results = []
    addresses_to_fetch = []
    new_caches_to_save = []

    try:
        cached_records = await repo.get_many(request.addresses)
        cache_map = {record.address: record for record in cached_records}

    except Exception as e:
        logger.error(f"Erro ao buscar lote no cache: {e}")
        cache_map = {}

    for address in request.addresses:
        if address in cache_map:
            cached = cache_map[address]
            final_results.append(
                GeocodingResponse(
                    source="cache",
                    data=GeocodingData(
                        place_id=cached.place_id,
                        address=cached.address,
                        latitude=cached.latitude,
                        longitude=cached.longitude,
                        formatted_address=cached.formatted_address
                    )
                )
            )

        else:
            addresses_to_fetch.append(address)

    if addresses_to_fetch:
        logger.info(f"Processando {len(addresses_to_fetch)} endereços de forma concorrente no Nominatim...")
        
        semaphore = asyncio.Semaphore(5) 

        async def fetch_address_with_semaphore(client: httpx.AsyncClient, addr: str):
            async with semaphore:
                try:
                    response = await client.get(
                        f"{NOMINATIM_URL}/search",
                        params={"q": addr, "format": "json", "addressdetails": 1, "limit": 1},
                        headers={"User-Agent": USER_AGENT},
                        timeout=15.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if data:
                        return addr, data[0]

                except Exception as e:
                    logger.error(f"Erro ao buscar '{addr}': {e}")
                
                return addr, None

        async with httpx.AsyncClient() as client:
            tasks = [
                fetch_address_with_semaphore(client, addr) 
                for addr in addresses_to_fetch
            ]
            
            results = await asyncio.gather(*tasks)

            for address, result_data in results:
                if result_data:
                    final_results.append(
                        GeocodingResponse(
                            source="nominatim",
                            data=GeocodingData(
                                place_id=str(result_data["place_id"]),
                                address=address,
                                latitude=float(result_data["latitude"]),
                                longitude=float(result_data["longitude"]),
                                formatted_address=result_data["display_name"]
                            )
                        )
                    )
                    
                    new_caches_to_save.append(
                        GeocodingCache(
                            address=address,
                            latitude=float(result_data["latitude"]),
                            longitude=float(result_data["longitude"]),
                            formatted_address=result_data["display_name"],
                            place_id=str(result_data["place_id"])
                        )
                    )

    if new_caches_to_save:
        try:
            await repo.add_many(new_caches_to_save, auto_commit=True)
            logger.info(f"{len(new_caches_to_save)} novos endereços salvos no cache em lote.")

        except Exception as e:
            logger.error(f"Erro ao salvar lote no cache: {e}")

    return BatchGeocodingResponse(results=final_results)


@router.get(
    "/reverse", 
    summary="Busca endereço a partir de Latitude e Longitude"
)
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    logger.info(f"Reverse geocoding requisitado para Lat: {lat}, Lon: {lon}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOMINATIM_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": USER_AGENT},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise HTTPException(status_code=404, detail="Nenhum endereço encontrado para essas coordenadas.")
                
            return {"source": "nominatim", "data": data}
            
        except httpx.RequestError as exc:
            logger.error(f"Erro de conexão com o Nominatim: {exc}")
            raise HTTPException(status_code=502, detail="Serviço de geocodificação indisponível.")


@router.post(
    "/reverse/batch", 
    response_model=BatchReverseGeocodingResponse,
    summary="Busca endereços a partir de múltiplas coordenadas em lote (Concorrente)"
)
async def batch_reverse_geocode(
    request: BatchReverseGeocodingRequest
):
    final_results = []
    
    if not request.coordinates:
        return BatchReverseGeocodingResponse(results=[])

    logger.info(f"Processando {len(request.coordinates)} coordenadas de forma concorrente no Nominatim...")
    
    semaphore = asyncio.Semaphore(5) 

    async def fetch_reverse_with_semaphore(client: httpx.AsyncClient, coord: CoordinateRequest):
        async with semaphore:
            try:
                response = await client.get(
                    f"{NOMINATIM_URL}/reverse",
                    params={"lat": coord.latitude, "lon": coord.longitude, "format": "json"},
                    headers={"User-Agent": USER_AGENT},
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" not in data:
                    return coord, data
                
            except Exception as e:
                logger.error(f"Erro ao buscar Latitude: {coord.latitude}, Longitude: {coord.longitude}: {e}")
            
            return coord, None

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_reverse_with_semaphore(client, coord) 
            for coord in request.coordinates
        ]
        
        results = await asyncio.gather(*tasks)

        for coord, result_data in results:
            if result_data:
                final_results.append(
                    ReverseGeocodingResult(
                        query=coord,
                        source="nominatim",
                        data=result_data
                    )
                )

            else:
                final_results.append(
                    ReverseGeocodingResult(
                        query=coord,
                        source="error",
                        data=None
                    )
                )

    return BatchReverseGeocodingResponse(results=final_results)