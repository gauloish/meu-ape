import os
import googlemaps

from logging import Logger

from pydantic import BaseModel


class GeocodingResult(BaseModel):
    ok: bool = False
    formatted_address: str = ""
    place_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


class GoogleMapsClient:
    def __init__(self, api_key: str | None, logger: Logger):
        if api_key is None:
            raise ValueError(f"Chave de API do Google Maps não fornecida.")

        self.client = googlemaps.Client(key=api_key)
        self.logger = logger

    def request(self, address: str) -> GeocodingResult:
        """Geocode a given address returning the formatted address, google place ID,
        and the latitude and longitude coordinates

        Args:
            address (str): Address to be coded

        Raises:
            Exception: If geocode does not find the address

        Returns:
            GeocodingResult: Geocode result with specified fields
        """
        result = self.client.geocode(address)

        if result:
            result = result[0]

            formatted_address = result["formatted_address"]
            place_id = result["place_id"]
            
            latitude = result["geometry"]["location"]["lat"]
            longitude = result["geometry"]["location"]["lng"]

            self.logger.info(f"Address(\"{address}\") successfully geocoded.")
            
        else:
            self.logger.error(f"Address(\"{address}\") failed to geocode.")

            return GeocodingResult()

        return GeocodingResult(
            ok=True,
            formatted_address=formatted_address,
            place_id=place_id,
            latitude=latitude,
            longitude=longitude,
        )
