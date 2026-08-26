import json
import logging
from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import GeocodingCache, ReverseGeocodingCache

logger = logging.getLogger(__name__)


def normalize_address(address: str) -> str:
    """Normalize address string for uniform cache lookup.

    Args:
        address (str): Raw input address.

    Returns:
        str: Cleaned, lowercased, and whitespace-collapsed address.
    """
    return " ".join(address.strip().lower().split())


class GeocodingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, address: str) -> GeocodingCache | None:
        """Return the geocoded persisted address from database.

        Args:
            address (str): Address whose geocoded version will be retrieved.

        Returns:
            GeocodingCache | None: Geocoded address object or None.
        """
        norm_addr = normalize_address(address)
        try:
            return await self.session.get(GeocodingCache, norm_addr)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching address '{address}': {e}")
            raise

    async def get_many(self, addresses: Iterable[str]) -> dict[str, GeocodingCache]:
        """Return multiple geocoded persisted addresses mapped by normalized address.

        Args:
            addresses (Iterable[str]): Addresses to be retrieved.

        Returns:
            dict[str, GeocodingCache]: Map of normalized_address -> GeocodingCache.
        """
        norm_map = {normalize_address(addr): addr for addr in addresses}
        if not norm_map:
            return {}

        try:
            stmt = select(GeocodingCache).where(GeocodingCache.address.in_(norm_map.keys()))
            result = await self.session.execute(stmt)
            records = result.scalars().all()
            return {record.address: record for record in records}
        except SQLAlchemyError as e:
            logger.error(f"Error fetching multiple addresses: {e}")
            raise

    async def add(self, geocoding: GeocodingCache, auto_commit: bool = True) -> None:
        """Add or update a geocoded address using PostgreSQL upsert.

        Args:
            geocoding (GeocodingCache): New geocoded address object.
            auto_commit (bool): If True, commits the transaction immediately.
        """
        await self.add_many([geocoding], auto_commit=auto_commit)

    async def add_many(self, geocodings: Iterable[GeocodingCache], auto_commit: bool = True) -> None:
        """Add or update multiple geocoded addresses using PostgreSQL upsert.

        Args:
            geocodings (Iterable[GeocodingCache]): List of geocoded objects.
            auto_commit (bool): If True, commits transaction.
        """
        items = list(geocodings)
        if not items:
            return

        # Deduplicate items by normalized address in Python memory first
        dedup_map: dict[str, GeocodingCache] = {}
        for item in items:
            norm_addr = normalize_address(item.address)
            item.address = norm_addr
            dedup_map[norm_addr] = item

        unique_items = list(dedup_map.values())

        try:
            stmt = pg_insert(GeocodingCache).values([
                {
                    "address": obj.address,
                    "latitude": obj.latitude,
                    "longitude": obj.longitude,
                    "formatted_address": obj.formatted_address,
                    "place_id": obj.place_id,
                }
                for obj in unique_items
            ])
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
            logger.error(f"Error adding multiple addresses to cache: {e}")
            raise


class ReverseGeocodingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, lat: float, lon: float) -> ReverseGeocodingCache | None:
        """Get reverse geocoding cache by coordinate.

        Args:
            lat (float): Latitude.
            lon (float): Longitude.

        Returns:
            ReverseGeocodingCache | None: Cached reverse result or None.
        """
        key = ReverseGeocodingCache.make_key(lat, lon)
        try:
            return await self.session.get(ReverseGeocodingCache, key)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching reverse cache for ({lat}, {lon}): {e}")
            raise

    async def get_many(self, coords: Iterable[tuple[float, float]]) -> dict[str, ReverseGeocodingCache]:
        """Get multiple reverse geocoding cache records by coordinate tuples.

        Args:
            coords (Iterable[tuple[float, float]]): List of (lat, lon) tuples.

        Returns:
            dict[str, ReverseGeocodingCache]: Map of coord_key -> ReverseGeocodingCache.
        """
        keys_map = {ReverseGeocodingCache.make_key(lat, lon): (lat, lon) for lat, lon in coords}
        if not keys_map:
            return {}

        try:
            stmt = select(ReverseGeocodingCache).where(ReverseGeocodingCache.coord_key.in_(keys_map.keys()))
            result = await self.session.execute(stmt)
            records = result.scalars().all()
            return {rec.coord_key: rec for rec in records}
        except SQLAlchemyError as e:
            logger.error(f"Error fetching multiple reverse cache entries: {e}")
            raise

    async def add(self, cache_obj: ReverseGeocodingCache, auto_commit: bool = True) -> None:
        """Add or update reverse geocoding cache record.

        Args:
            cache_obj (ReverseGeocodingCache): Cache record.
            auto_commit (bool): If True, commit.
        """
        await self.add_many([cache_obj], auto_commit=auto_commit)

    async def add_many(self, cache_objs: Iterable[ReverseGeocodingCache], auto_commit: bool = True) -> None:
        """Add or update multiple reverse geocoding cache records using upsert.

        Args:
            cache_objs (Iterable[ReverseGeocodingCache]): List of cache records.
            auto_commit (bool): If True, commit.
        """
        items = list(cache_objs)
        if not items:
            return

        dedup_map: dict[str, ReverseGeocodingCache] = {obj.coord_key: obj for obj in items}
        unique_items = list(dedup_map.values())

        try:
            stmt = pg_insert(ReverseGeocodingCache).values([
                {
                    "coord_key": obj.coord_key,
                    "latitude": obj.latitude,
                    "longitude": obj.longitude,
                    "raw_data_json": obj.raw_data_json,
                }
                for obj in unique_items
            ])
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