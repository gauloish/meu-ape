import requests
import logging

from logging import Logger
from pydantic import BaseModel

URL = f"http://localhost:8080/search"


logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class GeocodingResult(BaseModel):
    ok: bool = False
    formatted_address: str = ""
    place_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


class MapsClient:
    def __init__(self, logger: Logger):
        self.logger = logger

    def _request(self, address: str) -> GeocodingResult:
        """Geocode a given address returning the formatted address, place ID,
        and the latitude and longitude coordinates

        Args:
            address (str): Address to be coded

        Raises:
            Exception: If geocode does not find the address

        Returns:
            GeocodingResult: Geocode result with specified fields
        """
        params = {
            "q": address,
            "format": "jsonv2",
            "limit": 1,
        }

        response = requests.get(URL, params=params)

        if response and isinstance(response, list):
            result = response[0]

            formatted_address = result["display_name"]
            place_id = result["place_id"]
            
            latitude = result["lat"]
            longitude = result["lon"]

        else:

            return GeocodingResult()

        return GeocodingResult(
            ok=True,
            formatted_address=formatted_address,
            place_id=place_id,
            latitude=latitude,
            longitude=longitude,
        )

    def request(self, address: str) -> GeocodingResult:
        """Try geocode some equivalent combination of address
        with maps server API.

        Args:
            address (str): Address to be geocoded.

        Returns:
            GeocodingResult: Geocode result.
        """
        splits = address.split(",")

        street = splits[0]
        neighborhood = splits[1]

        queries = [
            f"{street}, {neighborhood}",
            f"{street}",
            f"{neighborhood}"
        ]

        for query in queries:
            result = self._request(query)

            if result.ok:
                break

        if not result.ok:
            self.logger.error(f"Address(\"{address}\") failed to geocode.")

        return result
