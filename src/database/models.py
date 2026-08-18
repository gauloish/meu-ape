"""SQLAlchemy ORM models for the meu-ape database schema.

Models:
    GeocodingCache: Cache of geocoded addresses to avoid redundant API calls.
    Listing: A real-estate property listing scraped from Zap Imóveis.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GeocodingCache(Base):
    __tablename__ = "geocoding_cache"

    address: Mapped[str] = mapped_column(String, primary_key=True, sqlite_on_conflict_primary_key="IGNORE")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    formatted_address: Mapped[str] = mapped_column(String)
    place_id: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return f"GeocodingCache(address={self.address}, latitude={self.latitude}, longitude={self.longitude})"


class Listing(Base):
    """A real-estate property listing scraped from Zap Imóveis.

    The ``listing_id`` is the canonical Zap identifier used as primary key.
    Uniqueness is enforced at the DB level, so upserts simply ignore conflicts.
    """

    __tablename__ = "listings"

    listing_id: Mapped[str] = mapped_column(String, primary_key=True)
    titulo: Mapped[str | None] = mapped_column(Text)
    tipo_imovel: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)
    preco: Mapped[float | None] = mapped_column(Float)
    moeda: Mapped[str | None] = mapped_column(String(10))
    condominio: Mapped[float | None] = mapped_column(Float)
    area_m2: Mapped[float | None] = mapped_column(Float)
    quartos: Mapped[int | None] = mapped_column(Integer)
    banheiros: Mapped[int | None] = mapped_column(Integer)
    vagas: Mapped[int | None] = mapped_column(Integer)
    bairro: Mapped[str | None] = mapped_column(String(200))
    rua: Mapped[str | None] = mapped_column(Text)
    cidade: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[str | None] = mapped_column(String(50))
    pais: Mapped[str | None] = mapped_column(String(50))
    aceita_pets: Mapped[str | None] = mapped_column(String(50))
    comodidades: Mapped[str | None] = mapped_column(Text)
    fotos_urls: Mapped[str | None] = mapped_column(Text)
    descricao_completa: Mapped[str | None] = mapped_column(Text)
    data_publicacao: Mapped[str | None] = mapped_column(String(50))
    data_modificacao: Mapped[str | None] = mapped_column(String(50))
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"Listing(id={self.listing_id!r}, tipo={self.tipo_imovel!r}, preco={self.preco})"
