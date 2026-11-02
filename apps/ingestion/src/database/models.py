"""SQLAlchemy ORM models for the meu-ape database schema.

Models:
    Listing: A real-estate property listing in Goiânia.
    ListingPriceHistory: Chronological price observation history for a property listing.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class Listing(Base):
    """A real-estate property listing stored in PostgreSQL.

    The ``listing_id`` is the canonical identifier used as primary key.
    Uniqueness is enforced by ``listing_id`` and canonical ``url`` at repository level.
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


class ListingPriceHistory(Base):
    """Chronological price and condominium fee record for a property listing."""

    __tablename__ = "listing_price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("listings.listing_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(Text)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    condominio: Mapped[float | None] = mapped_column(Float)
    moeda: Mapped[str | None] = mapped_column(String(10), default="BRL")
    fonte: Mapped[str | None] = mapped_column(String(50), default="zap_scrape")
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"ListingPriceHistory(listing_id={self.listing_id!r}, "
            f"preco={self.preco}, fonte={self.fonte!r})"
        )
