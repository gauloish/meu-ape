from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DeclarativeBase


def Base(DeclarativeBase):
    pass


class GeocodingCache(Base):
    __tablename__ = "geocoding_cache"

    address: Mapped[str] = mapped_column(String, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    formatted_address: Mapped[str] = mapped_column(String)
    place_id: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return f"GeoencodingCache(address={self.address}, latitude={self.latitude}, longitude={self.longitude})"
