from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import GeocodingCache


class GeocodingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, address: str) -> GeocodingCache | None:
        """Return the geocoded persisted address in database

        Args:
            address (str): Address whose geocoded version will be retrieved

        Returns:
            GeocodingCache | None: Geocoded address
        """
        return self.session.get(
            GeocodingCache,
            address,
        )

    def exists(self, address: str) -> bool:
        """Check if exists a geocoded version of given address in database

        Args:
            address (str): Address to be checked

        Returns:
            bool: `True` if the geocoded address is persisted
            in database. Otherwise, `False`
        """
        return self.get(address) is not None

    def add(self, geocoding: GeocodingCache) -> None:
        """Add a new geocoded address in the database

        Args:
            geocoding (GeocodingCache): New geocoded address to be
            added in the database
        """
        self.session.add(geocoding)

    def add_many(self, geocodings: Iterable[GeocodingCache]) -> None:
        """Add many geocoded addresses in the database

        Args:
            geocodings (Iterable[GeocodingCache]): A list of new
            geocoded addresses to be added in the database
        """
        self.session.add_all(geocodings)
