import json
from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GeocodingCache(Base):
    __tablename__ = "geocoding_cache"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    formatted_address: Mapped[str] = mapped_column(String, nullable=False)
    place_id: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"GeocodingCache(address='{self.address}', lat={self.latitude}, lon={self.longitude})"


class ReverseGeocodingCache(Base):
    __tablename__ = "reverse_geocoding_cache"

    coord_key: Mapped[str] = mapped_column(String, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    raw_data_json: Mapped[str] = mapped_column(Text, nullable=False)

    @classmethod
    def make_key(cls, lat: float, lon: float, precision: int = 5) -> str:
        """Create a normalized key from coordinates rounded to precision decimals (~1.1m)."""
        return f"{round(lat, precision):.{precision}f},{round(lon, precision):.{precision}f}"

    def get_data(self) -> dict:
        return json.loads(self.raw_data_json)

    def __repr__(self) -> str:
        return f"ReverseGeocodingCache(coord_key='{self.coord_key}')"
