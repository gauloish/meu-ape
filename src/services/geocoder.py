from logging import Logger
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from .maps import MapsClient
from .utils import normalize_text

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

        self.client = MapsClient(
            logger=self.logger,
        )

        Base.metadata.create_all(engine)

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
                normalized_address = normalize_text(address)
                result = repository.get(normalized_address)

                if result:
                    results[address] = GeocodingFeatures(
                        latitude=result.latitude,
                        longitude=result.longitude
                    )
                else:
                    unprocessed_addresses.append(address)

            unprocessed_addresses = list(set(unprocessed_addresses))
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                requests_results = executor.map(self.client.request, unprocessed_addresses)

            geocoded_results = zip(unprocessed_addresses, requests_results)
            geocoded_features = dict()

            for address, result in geocoded_results:
                if not result.ok:
                    continue

                normalized_address = normalize_text(address)

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

                if not repository.exists(normalized_address):
                    repository.add(geocoded_address)

            session.commit()
            
            results = results | geocoded_features

        return results