import os
import re
import unicodedata

from logging import Logger
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from . import GoogleMapsClient

from ..database import (
    Base,
    engine,
    Session,
    GeocodingCache,
    GeocodingRepository,
)

MAX_WORKERS: int = 8


class GeocodingFeatures(BaseModel):
    latitude: float
    longitude: float


class Geocoder:
    def __init__(self, logger: Logger):
        self.logger = logger

        self.client = GoogleMapsClient(
            api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
            logger=self.logger,
        )

        Base.metadata.create_all(engine)

    def _normalize_address(self, address: str) -> str:
        """Normalize address removing accents, exceded blank spaces,
        and put the string in upper case

        Args:
            address (str): Original address string

        Returns:
            str: Normalized address string
        """
        normalized_address = "".join(
            c
            for c in unicodedata.normalize("NFKD", address)
            if not unicodedata.combining(c)
        )

        normalized_address = re.sub(
            pattern=r"\s+",
            repl=" ",
            string=normalized_address
        )

        normalized_address = normalized_address.strip().upper()

        return normalized_address

    def geocode(self, addresses: List[str]) -> Dict[str, GeocodingFeatures]:
        """Geocode all given addresses, transforming it in coordinates (latitude and longitude)

        Args:
            addresses (List[str]): List of addresses

        Returns:
            Dict[str, GeocodingFeatures]: Mapping between addresses and the coordinates
        """
        results = {}

        with Session() as session:
            repository = GeocodingRepository(session)
            unprocessed_addresses = []

            for address in addresses:
                normalized_address = self._normalize_address(address)
                # TODO: Improve this query
                result = repository.get(normalized_address)

                if result:
                    results[address] = GeocodingFeatures(
                        latitude=result.latitude,
                        longitude=result.longitude
                    )
                else:
                    unprocessed_addresses.append(address)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                requests_results = executor.map(self.client.request, unprocessed_addresses)

            geocoded_results = zip(unprocessed_addresses, requests_results)
            geocoded_features = dict()
            geocoded_addresses = []

            for address, result in geocoded_results:
                if not result.ok:
                    continue

                normalized_address = self._normalize_address(address)

                geocoded_address = GeocodingCache(
                    address=normalized_address,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    formatted_address=result.formatted_address,
                    place_id=result.place_id,
                )

                geocoded_feature = GeocodingFeatures(
                    latitude=result.latitude,
                    longitude=result.longitude,
                )

                geocoded_features[normalized_address] = geocoded_feature
                geocoded_addresses.append(geocoded_address)

            repository.add_many(geocoded_addresses)
            session.commit()
            
            results = results | geocoded_features

        return results