from collections.abc import Iterable

from logging_config import config_logger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import GeocodingCache, ReverseGeocodingCache

config_logger()


def normalize_address(address: str) -> str:
    """Normaliza a string de endereço para uniformizar a busca na cache

    Args:
        address (str): Endereço bruto.

    Returns:
        str: Endereço limpo, com caracteres em minúsculo e sem espaços desnecessários.
    """
    return " ".join(address.strip().lower().split())


class GeocodingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, address: str) -> GeocodingCache | None:
        """
        Retorna o endereço persistido do banco de dados.

        Args:
            address (str): Endereço da busca.

        Returns:
            GeocodingCache | None: Geocodificação do endereço. Se não
            existir, retorna nulo.
        """
        norm_addr = normalize_address(address)

        try:
            return await self.session.get(GeocodingCache, norm_addr)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(f"Erro na busca das coordenadas do endereço '{address}': {e}")
            raise

    async def get_many(self, addresses: Iterable[str]) -> dict[str, GeocodingCache]:
        """Faz a busca para múltiplos endereços listados.

        Args:
            addresses (Iterable[str]): Endereços a serem buscados.

        Returns:
            dict[str, GeocodingCache]: Mapeamento dos endereços para as respectivas
            geocodificações.
        """
        norm_map = {normalize_address(addr): addr for addr in addresses}

        if not norm_map:
            return {}

        try:
            stmt = select(GeocodingCache).where(
                GeocodingCache.address.in_(norm_map.keys())
            )
            result = await self.session.execute(stmt)
            records = result.scalars().all()

            return {record.address: record for record in records}

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"Erro ao fazer a busca das coordenadas de mútiplos endereços: {e}"
            )

            raise

    async def add(self, geocoding: GeocodingCache, auto_commit: bool = True) -> None:
        """Adiciona/atualiza um novo endereço geocodificado no banco de dados.

        Args:
            geocoding (GeocodingCache): Novo objeto de endereço geocodificado.
            auto_commit (bool): Se True, comita a transação imediatamente no banco de dados.
        """
        await self.add_many([geocoding], auto_commit=auto_commit)

    async def add_many(
        self, geocodings: Iterable[GeocodingCache], auto_commit: bool = True
    ) -> None:
        """Adiciona/atualiza múltiplos endereços geocodificados no banco de dados.

        Args:
            geocodings (Iterable[GeocodingCache]): Lista dos objetos de endereço geocodificados.
            auto_commit (bool): Se True, comita a transação imediatamente no banco de dados.
        """
        items = list(geocodings)

        if not items:
            return

        dedup_map: dict[str, GeocodingCache] = {}

        for item in items:
            norm_addr = normalize_address(item.address)
            item.address = norm_addr
            dedup_map[norm_addr] = item

        unique_items = list(dedup_map.values())

        try:
            stmt = pg_insert(GeocodingCache).values(
                [
                    {
                        "address": obj.address,
                        "latitude": obj.latitude,
                        "longitude": obj.longitude,
                        "formatted_address": obj.formatted_address,
                        "place_id": obj.place_id,
                    }
                    for obj in unique_items
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["address"],
                set_={
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "formatted_address": stmt.excluded.formatted_address,
                    "place_id": stmt.excluded.place_id,
                },
            )

            await self.session.execute(stmt)

            if auto_commit:
                await self.session.commit()
            else:
                await self.session.flush()

        except SQLAlchemyError as e:
            if auto_commit:
                await self.session.rollback()

            logger.error(
                f"Erro ao adicionar múltiplos endereços ao banco de dados: {e}"
            )
            raise


class ReverseGeocodingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, lat: float, lon: float) -> ReverseGeocodingCache | None:
        """Obtém o endereço (rua e bairro) dadas as coordenadas de entrada (geocodificação reversa).

        Args:
            lat (float): Latitude.
            lon (float): Longitude.

        Returns:
            ReverseGeocodingCache | None: Endereço buscado. Se não encontrado, retorna nulo.
        """
        key = ReverseGeocodingCache.make_key(lat, lon)

        try:
            return await self.session.get(ReverseGeocodingCache, key)

        except SQLAlchemyError as e:
            await self.session.rollback()

            logger.error(
                f"Erro ao fazer a busca pelo endereços das coordenadas ({lat}, {lon}): {e}"
            )
            raise

    async def get_many(
        self, coords: Iterable[tuple[float, float]]
    ) -> dict[str, ReverseGeocodingCache]:
        """
        Get multiple reverse geocoding cache records by coordinate tuples.

        Args:
            coords (Iterable[tuple[float, float]]): List of (lat, lon) tuples.

        Returns:
            dict[str, ReverseGeocodingCache]: Map of coord_key -> ReverseGeocodingCache.
        """
        keys_map = {
            ReverseGeocodingCache.make_key(lat, lon): (lat, lon) for lat, lon in coords
        }

        if not keys_map:
            return {}

        try:
            stmt = select(ReverseGeocodingCache).where(
                ReverseGeocodingCache.coord_key.in_(keys_map.keys())
            )
            result = await self.session.execute(stmt)
            records = result.scalars().all()
            return {rec.coord_key: rec for rec in records}
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"Erro ao fazer a busca dos endereços de múltiplas coordenadas: {e}"
            )
            raise

    async def add(
        self, cache_obj: ReverseGeocodingCache, auto_commit: bool = True
    ) -> None:
        """Adicionar/atualizar o objeto

        Args:
            cache_obj (ReverseGeocodingCache): Cache record.
            auto_commit (bool): If True, commit.
        """
        await self.add_many([cache_obj], auto_commit=auto_commit)

    async def add_many(
        self, cache_objs: Iterable[ReverseGeocodingCache], auto_commit: bool = True
    ) -> None:
        """Add or update multiple reverse geocoding cache records using upsert.

        Args:
            cache_objs (Iterable[ReverseGeocodingCache]): List of cache records.
            auto_commit (bool): If True, commit.
        """
        items = list(cache_objs)
        if not items:
            return

        dedup_map: dict[str, ReverseGeocodingCache] = {
            obj.coord_key: obj for obj in items
        }
        unique_items = list(dedup_map.values())

        try:
            stmt = pg_insert(ReverseGeocodingCache).values(
                [
                    {
                        "coord_key": obj.coord_key,
                        "latitude": obj.latitude,
                        "longitude": obj.longitude,
                        "raw_data_json": obj.raw_data_json,
                    }
                    for obj in unique_items
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["coord_key"],
                set_={
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "raw_data_json": stmt.excluded.raw_data_json,
                },
            )

            await self.session.execute(stmt)

            if auto_commit:
                await self.session.commit()
            else:
                await self.session.flush()

        except SQLAlchemyError as e:
            if auto_commit:
                await self.session.rollback()
            logger.error(f"Error adding multiple reverse geocoding entries: {e}")
            raise
