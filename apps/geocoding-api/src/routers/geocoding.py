import asyncio
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.models import GeocodingCache, ReverseGeocodingCache
from ..database.repositories import (
    GeocodingRepository,
    ReverseGeocodingRepository,
    normalize_address,
)
from ..dependencies import get_db, get_http_client
from ..rate_limiter import get_rate_limit_batch, get_rate_limit_default, limiter
from ..schemas import (
    BatchGeocodingRequest,
    BatchGeocodingResponse,
    BatchReverseGeocodingRequest,
    BatchReverseGeocodingResponse,
    CoordinateRequest,
    GeocodingData,
    GeocodingResponse,
    ReverseGeocodingResponse,
    ReverseGeocodingResult,
)
from ..security import verify_api_key
from logging_settings import setup_logger

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/geocoding",
    tags=["Geocoding"],
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/search",
    response_model=GeocodingResponse,
    summary="Busca coordenadas por endereço (com cache no PostgreSQL)",
)
@limiter.limit(get_rate_limit_default)
async def search_address(
    request: Request,
    address: str = Query(..., description="Endereço completo para buscar"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> GeocodingResponse:
    repo = GeocodingRepository(db)

    # 1. Consulta o cache no PostgreSQL
    try:
        cached_address = await repo.get(address)
        if cached_address:
            logger.info(f"Cache HIT para o endereço: '{address}'")
            return GeocodingResponse(
                source="cache",
                data=GeocodingData(
                    place_id=cached_address.place_id,
                    address=address,
                    latitude=cached_address.latitude,
                    longitude=cached_address.longitude,
                    formatted_address=cached_address.formatted_address,
                ),
            )
    except Exception as e:
        logger.error(f"Erro ao consultar o cache para '{address}': {e}")

    # 2. Cache MISS — Consulta o Nominatim
    logger.info(f"Cache MISS. Buscando '{address}' no Nominatim...")
    try:
        response = await client.get(
            f"{settings.nominatim_url}/search",
            params={"q": address, "format": "json", "addressdetails": 1, "limit": 1},
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endereço não encontrado no mapa.",
            )

        first_result = data[0]
        lat_val = float(first_result["lat"])
        lon_val = float(first_result["lon"])
        place_id_str = str(first_result["place_id"])
        formatted_addr = first_result.get("display_name", address)

        # 3. Salva no cache com upsert
        new_cache = GeocodingCache(
            address=address,
            latitude=lat_val,
            longitude=lon_val,
            formatted_address=formatted_addr,
            place_id=place_id_str,
        )

        try:
            await repo.add(new_cache, auto_commit=True)
            logger.info(f"Novo endereço salvo no cache: '{address}'")
        except Exception as e:
            logger.error(f"Não foi possível salvar no cache: {e}")

        return GeocodingResponse(
            source="nominatim",
            data=GeocodingData(
                place_id=place_id_str,
                address=address,
                latitude=lat_val,
                longitude=lon_val,
                formatted_address=formatted_addr,
            ),
        )

    except httpx.RequestError as exc:
        logger.error(f"Erro de conexão com o Nominatim ao buscar '{address}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serviço de geocodificação indisponível.",
        )


@router.post(
    "/search/batch",
    response_model=BatchGeocodingResponse,
    summary="Busca coordenadas para múltiplos endereços em lote (Concorrente com Cache)",
)
@limiter.limit(get_rate_limit_batch)
async def batch_search_address(
    request: Request,
    body: BatchGeocodingRequest,
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> BatchGeocodingResponse:
    repo = GeocodingRepository(db)
    final_results_map: dict[str, GeocodingResponse] = {}
    addresses_to_fetch: list[str] = []

    # Desduplica mantendo a ordem original
    unique_addresses = list(dict.fromkeys(body.addresses))

    # 1. Consulta o cache em lote
    try:
        cache_map = await repo.get_many(unique_addresses)
    except Exception as e:
        logger.error(f"Erro ao consultar lote no cache: {e}")
        cache_map = {}

    for addr in unique_addresses:
        norm_key = normalize_address(addr)
        if norm_key in cache_map:
            cached = cache_map[norm_key]
            final_results_map[addr] = GeocodingResponse(
                source="cache",
                data=GeocodingData(
                    place_id=cached.place_id,
                    address=addr,
                    latitude=cached.latitude,
                    longitude=cached.longitude,
                    formatted_address=cached.formatted_address,
                ),
            )
        else:
            addresses_to_fetch.append(addr)

    # 2. Busca endereços restantes concorrentemente no Nominatim
    if addresses_to_fetch:
        logger.info(f"Processando {len(addresses_to_fetch)} endereços de forma concorrente no Nominatim...")
        semaphore = asyncio.Semaphore(10)
        new_caches_to_save: list[GeocodingCache] = []

        async def fetch_address(addr: str) -> tuple[str, dict | None]:
            async with semaphore:
                try:
                    res = await client.get(
                        f"{settings.nominatim_url}/search",
                        params={
                            "q": addr,
                            "format": "json",
                            "addressdetails": 1,
                            "limit": 1,
                        },
                    )
                    res.raise_for_status()
                    data = res.json()
                    if data:
                        return addr, data[0]
                except Exception as e:
                    logger.error(f"Erro ao buscar endereço em lote '{addr}': {e}")
                return addr, None

        tasks = [fetch_address(addr) for addr in addresses_to_fetch]
        fetched_results = await asyncio.gather(*tasks)

        for addr, result_data in fetched_results:
            if result_data:
                lat_val = float(result_data["lat"])
                lon_val = float(result_data["lon"])
                place_id_str = str(result_data["place_id"])
                formatted_addr = result_data.get("display_name", addr)

                res_obj = GeocodingResponse(
                    source="nominatim",
                    data=GeocodingData(
                        place_id=place_id_str,
                        address=addr,
                        latitude=lat_val,
                        longitude=lon_val,
                        formatted_address=formatted_addr,
                    ),
                )
                final_results_map[addr] = res_obj

                new_caches_to_save.append(
                    GeocodingCache(
                        address=addr,
                        latitude=lat_val,
                        longitude=lon_val,
                        formatted_address=formatted_addr,
                        place_id=place_id_str,
                    )
                )

        # 3. Salva novos resultados no cache de forma atômica/upsert
        if new_caches_to_save:
            try:
                await repo.add_many(new_caches_to_save, auto_commit=True)
                logger.info(f"{len(new_caches_to_save)} novos endereços salvos no cache em lote.")
            except Exception as e:
                logger.error(f"Erro ao salvar lote de endereços no cache: {e}")

    # Reorganiza os resultados mantendo a ordem original da requisição (incluindo duplicados)
    ordered_results = [
        final_results_map.get(
            addr,
            GeocodingResponse(
                source="error",
                data=GeocodingData(
                    place_id="",
                    address=addr,
                    latitude=0.0,
                    longitude=0.0,
                    formatted_address="Endereço não encontrado",
                ),
            ),
        )
        for addr in body.addresses
    ]

    return BatchGeocodingResponse(results=ordered_results)


@router.get(
    "/reverse",
    response_model=ReverseGeocodingResponse,
    summary="Busca endereço a partir de Latitude e Longitude (com cache)",
)
@limiter.limit(get_rate_limit_default)
async def reverse_geocode(
    request: Request,
    lat: float = Query(..., description="Latitude", ge=-90.0, le=90.0),
    lon: float = Query(..., description="Longitude", ge=-180.0, le=180.0),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> ReverseGeocodingResponse:
    logger.info(f"Reverse geocoding requisitado para Lat: {lat}, Lon: {lon}")
    rev_repo = ReverseGeocodingRepository(db)

    # 1. Verifica cache no PostgreSQL
    try:
        cached = await rev_repo.get(lat, lon)
        if cached:
            logger.info(f"Reverse cache HIT para Lat: {lat}, Lon: {lon}")
            return ReverseGeocodingResponse(source="cache", data=cached.get_data())
    except Exception as e:
        logger.error(f"Erro ao consultar cache de reverse geocoding: {e}")

    # 2. Cache MISS — Consulta o Nominatim
    try:
        response = await client.get(
            f"{settings.nominatim_url}/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum endereço encontrado para essas coordenadas.",
            )

        # 3. Salva no cache
        key = ReverseGeocodingCache.make_key(lat, lon)
        new_cache = ReverseGeocodingCache(
            coord_key=key,
            latitude=lat,
            longitude=lon,
            raw_data_json=json.dumps(data),
        )
        try:
            await rev_repo.add(new_cache, auto_commit=True)
            logger.info(f"Novo reverse geocode salvo no cache para Lat: {lat}, Lon: {lon}")
        except Exception as e:
            logger.error(f"Erro ao salvar reverse cache no banco: {e}")

        return ReverseGeocodingResponse(source="nominatim", data=data)

    except httpx.RequestError as exc:
        logger.error(f"Erro de conexão com o Nominatim no reverse geocoding: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serviço de geocodificação indisponível.",
        )


@router.post(
    "/reverse/batch",
    response_model=BatchReverseGeocodingResponse,
    summary="Busca endereços a partir de múltiplas coordenadas em lote (Concorrente com Cache)",
)
@limiter.limit(get_rate_limit_batch)
async def batch_reverse_geocode(
    request: Request,
    body: BatchReverseGeocodingRequest,
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> BatchReverseGeocodingResponse:
    if not body.coordinates:
        return BatchReverseGeocodingResponse(results=[])

    rev_repo = ReverseGeocodingRepository(db)
    final_results_map: dict[str, ReverseGeocodingResult] = {}
    coords_to_fetch: list[CoordinateRequest] = []

    coord_tuples = [(c.latitude, c.longitude) for c in body.coordinates]

    # 1. Consulta cache em lote
    try:
        cache_map = await rev_repo.get_many(coord_tuples)
    except Exception as e:
        logger.error(f"Erro ao buscar lote no cache de reverse: {e}")
        cache_map = {}

    for coord in body.coordinates:
        key = ReverseGeocodingCache.make_key(coord.latitude, coord.longitude)
        if key in cache_map:
            cached_rec = cache_map[key]
            final_results_map[key] = ReverseGeocodingResult(
                query=coord,
                source="cache",
                data=cached_rec.get_data(),
            )
        else:
            coords_to_fetch.append(coord)

    # 2. Busca coordenadas faltantes no Nominatim de forma concorrente
    if coords_to_fetch:
        logger.info(f"Processando {len(coords_to_fetch)} coordenadas em lote no Nominatim...")
        semaphore = asyncio.Semaphore(10)
        new_caches_to_save: list[ReverseGeocodingCache] = []

        async def fetch_reverse(c: CoordinateRequest) -> tuple[CoordinateRequest, dict | None]:
            async with semaphore:
                try:
                    res = await client.get(
                        f"{settings.nominatim_url}/reverse",
                        params={"lat": c.latitude, "lon": c.longitude, "format": "json"},
                    )
                    res.raise_for_status()
                    data = res.json()
                    if "error" not in data:
                        return c, data
                except Exception as e:
                    logger.error(f"Erro ao buscar reverse para ({c.latitude}, {c.longitude}): {e}")
                return c, None

        tasks = [fetch_reverse(c) for c in coords_to_fetch]
        fetched_results = await asyncio.gather(*tasks)

        for coord_req, result_data in fetched_results:
            key = ReverseGeocodingCache.make_key(coord_req.latitude, coord_req.longitude)
            if result_data:
                final_results_map[key] = ReverseGeocodingResult(
                    query=coord_req,
                    source="nominatim",
                    data=result_data,
                )
                new_caches_to_save.append(
                    ReverseGeocodingCache(
                        coord_key=key,
                        latitude=coord_req.latitude,
                        longitude=coord_req.longitude,
                        raw_data_json=json.dumps(result_data),
                    )
                )
            else:
                final_results_map[key] = ReverseGeocodingResult(
                    query=coord_req,
                    source="error",
                    data=None,
                )

        # 3. Salva no cache os novos itens
        if new_caches_to_save:
            try:
                await rev_repo.add_many(new_caches_to_save, auto_commit=True)
                logger.info(f"{len(new_caches_to_save)} novas coordenadas salvas no cache reverse em lote.")
            except Exception as e:
                logger.error(f"Erro ao salvar lote de reverse no cache: {e}")

    # Reorganiza os resultados na ordem original das requisições
    ordered_results = [
        final_results_map.get(
            ReverseGeocodingCache.make_key(c.latitude, c.longitude),
            ReverseGeocodingResult(query=c, source="error", data=None),
        )
        for c in body.coordinates
    ]

    return BatchReverseGeocodingResponse(results=ordered_results)