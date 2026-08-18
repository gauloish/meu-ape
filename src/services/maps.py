import requests
import logging

from logging import Logger
from pydantic import BaseModel

from .utils import check_normalized_substring

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

    def _request(self, street: str, neighborhood: str, address: str) -> GeocodingResult:
        params = {
            "q": address,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }

        response = requests.get(URL, params=params)
        fallback_response = GeocodingResult()

        if response.status_code == 200:
            result = response.json()

            if not isinstance(result, list):
                return fallback_response

            if len(result) == 0:
                return fallback_response
            
            result = result[0]

            formatted_address = result["display_name"]
            address_info = result["address"]

            valid_result = True

            city = address_info.get("city", "")
            road = address_info.get("road", "")
            suburb = address_info.get("suburb", "")

            if (city != "") and (not check_normalized_substring(city, "Goiânia")):
                self.logger.warning(f"1. Address(street=\"{street}\", neighborhood=\"{neighborhood}\", address=\"{road}, {suburb}, {city}\")")
                valid_result = False
            elif (road != "") and (street != "") and (not check_normalized_substring(road, street)):
                self.logger.warning(f"2. Address(street=\"{street}\", neighborhood=\"{neighborhood}\", address=\"{road}, {suburb}, {city}\")")
                valid_result = False
            elif (suburb != "") and (neighborhood != "") and (not check_normalized_substring(suburb, neighborhood)):
                self.logger.warning(f"3. Address(street=\"{street}\", neighborhood=\"{neighborhood}\", address=\"{road}, {suburb}, {city}\")")
                valid_result = False

            if not valid_result:
                # self.logger.warning(f"Address(street=\"{street}\", neighborhood=\"{neighborhood}\", address=\"{road}, {suburb}, {city}\")")

                return fallback_response

            place_id = str(result["place_id"])
            
            latitude = float(result["lat"])
            longitude = float(result["lon"])

            return GeocodingResult(
                ok=True,
                formatted_address=formatted_address,
                place_id=place_id,
                latitude=latitude,
                longitude=longitude,
            )

        return fallback_response


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
        neighborhood = splits[1].strip()

        queries = [
            (street, neighborhood, f"{street}, {neighborhood}"),
            (street, "", street),
            ("", neighborhood, neighborhood),
        ]

        for _street, _neighborhood, _address in queries:
            result = self._request(_street, _neighborhood, _address)

            if result.ok:
                break

        if not result.ok:
            # self.logger.error(f"Address(address=\"{address}\") failed to geocode.")
            pass

        return result
