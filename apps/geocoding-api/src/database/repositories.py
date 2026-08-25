import logging
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import GeocodingCache


logger = logging.getLogger(__name__)


class GeocodingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, address: str) -> GeocodingCache | None:
        """Return the geocoded persisted address in database

        Args:
            address (str): Address whose geocoded version will be retrieved

        Returns:
            GeocodingCache | None: Geocoded address
        """
        try:
            return await self.session.get(GeocodingCache, address)

        except SQLAlchemyError as e:
            logger.error(f"Error to get address '{address}': {e}")
            raise

    async def get_many(self, addresses: Iterable[str]) -> Sequence[GeocodingCache]:
        """Return multiple geocoded persisted addresses in database

        Args:
            addresses (Iterable[str]): Addresses to be retrieved

        Returns:
            Sequence[GeocodingCache]: List of geocoded addresses found
        """
        try:
            stmt = select(GeocodingCache).where(GeocodingCache.address.in_(addresses))
            result = await self.session.execute(stmt)

            return result.scalars().all()

        except SQLAlchemyError as e:
            logger.error(f"Error to get multiple addresses: {e}")
            raise

    async def exists(self, address: str) -> bool:
        """Check if exists a geocoded version of given address in database

        Args:
            address (str): Address to be checked

        Returns:
            bool: `True` if the geocoded address is persisted
            in database. Otherwise, `False`
        """
        return await self.get(address) is not None

    async def add(self, geocoding: GeocodingCache, auto_commit: bool = True) -> None:
        """Add a new geocoded address in the database

        Args:
            geocoding (GeocodingCache): New geocoded address to be added
            auto_commit (bool): If True, commits the transaction immediately.
        """
        try:
            self.session.add(geocoding)

            if auto_commit:
                await self.session.commit()
            else:
                await self.session.flush()

        except SQLAlchemyError as e:
            if auto_commit:
                await self.session.rollback()

            logger.error(f"Error to add addresses '{geocoding.address}': {e}")
            raise

    async def add_many(self, geocodings: Iterable[GeocodingCache], auto_commit: bool = True) -> None:
        """Add many geocoded addresses in the database

        Args:
            geocodings (Iterable[GeocodingCache]): A list of new geocoded addresses
            auto_commit (bool): If True, commits the transaction immediately.
        """
        try:
            self.session.add_all(geocodings)

            if auto_commit:
                await self.session.commit()
            else:
                await self.session.flush()

        except SQLAlchemyError as e:
            if auto_commit:
                await self.session.rollback()

            logger.error(f"Error to add multiple addresses: {e}")
            raise