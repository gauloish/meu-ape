import logging

from logging import Logger
from pydantic import BaseModel
from geopy.geocoders import Nominatim


URL = f"http://localhost:8080/search"

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("geopy").setLevel(logging.WARNING)


class GeocodingResult(BaseModel):
    ok: bool = False
    formatted_address: str = ""
    place_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


class MapsClient:
    def __init__(self, logger: Logger):
        self.logger = logger

        self.geolocator  = Nominatim(
            user_agent="geocoder",
            domain="localhost:8080",
            scheme="http",
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

        street = splits[0].strip()
        suburb = splits[1].strip()

        queries = [f"{street}, {suburb}", suburb, street]
        result = GeocodingResult()

        for query in queries:
            try:
                location = self.geolocator.geocode(
                    query=query,
                    exactly_one=True,
                    country_codes="BR",
                )

                if location:
                    formatted_address = location.address
                    place_id = str(location.raw["place_id"])
                    latitude = location.latitude
                    longitude = location.longitude

                    result = GeocodingResult(
                        ok=True,
                        formatted_address=formatted_address,
                        place_id=place_id,
                        latitude=latitude,
                        longitude=longitude,
                    )

                    self.logger.info(f"Address(original=\"{address}\", found=\"{formatted_address}\")")

                    break

            except Exception as error:
                self.logger.warning(f"Error to process Address(addres={address}): {error}")

        return result
