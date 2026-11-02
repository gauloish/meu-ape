"""Repository implementations for database entity access, URL/ID deduplication, and price history."""

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Listing, ListingPriceHistory
from src.scraping.zap_parser import extract_id_from_url, normalize_url


def _safe_float(val: Any) -> float | None:
    if val is None or pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> int | None:
    if val is None or pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _parse_scraped_at(raw_scraped: Any) -> datetime:
    """Convert raw scraped_at value to a datetime object."""
    if isinstance(raw_scraped, str) and not pd.isna(raw_scraped):
        try:
            return datetime.fromisoformat(raw_scraped)
        except (ValueError, TypeError):
            return datetime.now(UTC)
    if isinstance(raw_scraped, datetime):
        return raw_scraped
    return datetime.now(UTC)


class ListingRepository:
    """Repository managing property listing persistence, ID/URL deduplication, and price history."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_ids(self) -> set[str]:
        """Fetch set of all listing IDs currently stored in the database.

        Returns:
            Set of listing ID strings.
        """
        stmt = select(Listing.listing_id)
        results = self.session.scalars(stmt).all()
        return set(results)

    def get_all_urls(self) -> set[str]:
        """Fetch set of all normalised listing URLs currently stored in the database.

        Returns:
            Set of normalised URL strings.
        """
        stmt = select(Listing.url).where(Listing.url.is_not(None))
        results = self.session.scalars(stmt).all()
        return {norm for u in results if u and (norm := normalize_url(u)) is not None}

    def get_existing_ids(self, listing_ids: Iterable[str]) -> set[str]:
        """Query database for listing IDs that are already persisted.

        Args:
            listing_ids: Collection of listing IDs to check.

        Returns:
            Set of listing IDs present in the database.
        """
        ids_list = [str(i) for i in listing_ids if i and not pd.isna(i)]
        if not ids_list:
            return set()

        existing: set[str] = set()
        chunk_size = 500
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i : i + chunk_size]
            stmt = select(Listing.listing_id).where(Listing.listing_id.in_(chunk))
            results = self.session.scalars(stmt).all()
            existing.update(results)
        return existing

    def get_existing_urls(self, urls: Iterable[str]) -> set[str]:
        """Query database for normalised listing URLs that are already persisted.

        Args:
            urls: Collection of listing URLs to check.

        Returns:
            Set of normalised URLs present in the database.
        """
        norm_list = [
            norm
            for u in urls
            if u and not pd.isna(u) and (norm := normalize_url(str(u))) is not None
        ]
        if not norm_list:
            return set()

        existing: set[str] = set()
        chunk_size = 500
        for i in range(0, len(norm_list), chunk_size):
            chunk = norm_list[i : i + chunk_size]
            stmt = select(Listing.url).where(Listing.url.in_(chunk))
            results = self.session.scalars(stmt).all()
            for res_url in results:
                if res_url and (norm := normalize_url(res_url)) is not None:
                    existing.add(norm)
        return existing

    def _get_existing_by_ids_or_urls(
        self, listing_ids: Iterable[str], urls: Iterable[str]
    ) -> tuple[dict[str, Listing], dict[str, Listing]]:
        """Load existing Listing entities matched by ID or normalised URL."""
        by_id: dict[str, Listing] = {}
        by_url: dict[str, Listing] = {}

        ids_list = [str(i) for i in listing_ids if i]
        chunk_size = 500
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i : i + chunk_size]
            stmt = select(Listing).where(Listing.listing_id.in_(chunk))
            for obj in self.session.scalars(stmt).all():
                by_id[obj.listing_id] = obj
                if obj.url and (norm := normalize_url(obj.url)):
                    by_url[norm] = obj

        urls_list = [u for u in urls if u and u not in by_url]
        for i in range(0, len(urls_list), chunk_size):
            chunk = urls_list[i : i + chunk_size]
            stmt = select(Listing).where(Listing.url.in_(chunk))
            for obj in self.session.scalars(stmt).all():
                by_id[obj.listing_id] = obj
                if obj.url and (norm := normalize_url(obj.url)):
                    by_url[norm] = obj

        return by_id, by_url

    def add_many(
        self, records: list[dict[str, Any]], source: str = "zap_scrape"
    ) -> int:
        """Insert new listing records and track price history changes for existing listings.

        Deduplicates both within the batch and against the database by ``listing_id``
        and canonical ``url``. When an existing listing has a new price, updates the
        listing price and records a new entry in ``listing_price_history``.

        Args:
            records: List of parsed listing dictionaries.
            source: Identifier of the data source for price history tracking.

        Returns:
            Count of newly inserted listings.
        """
        if not records:
            return 0

        unique_records: dict[str, dict[str, Any]] = {}
        seen_batch_urls: set[str] = set()

        for r in records:
            raw_url = _safe_str(r.get("url"))
            norm_url = normalize_url(raw_url) if raw_url else None
            raw_id = (
                r.get("id")
                or r.get("listing_id")
                or extract_id_from_url(norm_url or raw_url)
            )
            lid = _safe_str(raw_id)
            if not lid:
                continue
            if lid in unique_records:
                continue
            if norm_url and norm_url in seen_batch_urls:
                continue

            enriched = dict(r)
            enriched["_resolved_id"] = lid
            enriched["_resolved_url"] = norm_url or raw_url
            unique_records[lid] = enriched
            if norm_url:
                seen_batch_urls.add(norm_url)

        if not unique_records:
            return 0

        existing_by_id, existing_by_url = self._get_existing_by_ids_or_urls(
            unique_records.keys(), seen_batch_urls
        )

        objs: list[Listing] = []
        history_objs: list[ListingPriceHistory] = []
        updated_existing = False

        for lid, r in unique_records.items():
            resolved_url = r.get("_resolved_url")
            scraped_dt = _parse_scraped_at(r.get("scraped_at"))
            new_price = _safe_float(r.get("preco"))
            new_condo = _safe_float(r.get("condominio"))
            moeda = _safe_str(r.get("moeda")) or "BRL"

            existing = existing_by_id.get(lid) or (
                existing_by_url.get(resolved_url) if resolved_url else None
            )
            if existing is not None:
                if new_price is not None and (
                    existing.preco is None or abs(existing.preco - new_price) > 1e-2
                ):
                    existing.preco = new_price
                    if new_condo is not None:
                        existing.condominio = new_condo
                    if mod := _safe_str(r.get("data_modificacao")):
                        existing.data_modificacao = mod
                    existing.scraped_at = scraped_dt
                    history_objs.append(
                        ListingPriceHistory(
                            listing_id=existing.listing_id,
                            url=existing.url or resolved_url,
                            preco=new_price,
                            condominio=(
                                new_condo
                                if new_condo is not None
                                else existing.condominio
                            ),
                            moeda=moeda,
                            fonte=source,
                            observed_at=scraped_dt,
                        )
                    )
                    updated_existing = True
                continue

            objs.append(
                Listing(
                    listing_id=lid,
                    titulo=_safe_str(r.get("titulo")),
                    tipo_imovel=_safe_str(r.get("tipo_imovel")),
                    url=resolved_url,
                    preco=new_price,
                    moeda=_safe_str(r.get("moeda")),
                    condominio=new_condo,
                    area_m2=_safe_float(r.get("area_m2")),
                    quartos=_safe_int(r.get("quartos")),
                    banheiros=_safe_int(r.get("banheiros")),
                    vagas=_safe_int(r.get("vagas")),
                    bairro=_safe_str(r.get("bairro")),
                    rua=_safe_str(r.get("rua")),
                    cidade=_safe_str(r.get("cidade")),
                    estado=_safe_str(r.get("estado")),
                    pais=_safe_str(r.get("pais")),
                    aceita_pets=_safe_str(r.get("aceita_pets")),
                    comodidades=_safe_str(r.get("comodidades")),
                    fotos_urls=_safe_str(r.get("fotos_urls")),
                    descricao_completa=_safe_str(r.get("descricao_completa")),
                    data_publicacao=_safe_str(r.get("data_publicacao")),
                    data_modificacao=_safe_str(r.get("data_modificacao")),
                    scraped_at=scraped_dt,
                )
            )
            if new_price is not None:
                history_objs.append(
                    ListingPriceHistory(
                        listing_id=lid,
                        url=resolved_url,
                        preco=new_price,
                        condominio=new_condo,
                        moeda=moeda,
                        fonte=source,
                        observed_at=scraped_dt,
                    )
                )

        if not objs and not history_objs and not updated_existing:
            return 0

        if objs:
            self.session.add_all(objs)
        if history_objs:
            self.session.add_all(history_objs)
        self.session.commit()
        return len(objs)

    def get_price_history(self, listing_id: str) -> list[ListingPriceHistory]:
        """Return chronological price history entries for a specific listing.

        Args:
            listing_id: Canonical listing ID string.

        Returns:
            List of ListingPriceHistory instances ordered by observation time.
        """
        stmt = (
            select(ListingPriceHistory)
            .where(ListingPriceHistory.listing_id == str(listing_id))
            .order_by(
                ListingPriceHistory.observed_at.asc(), ListingPriceHistory.id.asc()
            )
        )
        return list(self.session.scalars(stmt).all())

    def apply_price_index(
        self,
        factor: float,
        source: str = "fipezap_index",
        observed_at: datetime | None = None,
    ) -> int:
        """Apply a multiplicative price index factor to all priced listings and record history.

        Args:
            factor: Multiplicative adjustment factor (e.g. 1.0078 for +0.78%).
            source: Label identifying the index adjustment source.
            observed_at: Timestamp of the adjustment (defaults to current UTC time).

        Returns:
            Number of listings updated.
        """
        if abs(factor - 1.0) < 1e-9:
            return 0

        ts = observed_at or datetime.now(UTC)
        stmt = select(Listing).where(Listing.preco.is_not(None))
        listings = list(self.session.scalars(stmt).all())
        if not listings:
            return 0

        history_objs: list[ListingPriceHistory] = []
        for listing in listings:
            if listing.preco is None:
                continue
            adjusted_price = round(float(listing.preco) * factor, 2)
            listing.preco = adjusted_price
            listing.scraped_at = ts
            history_objs.append(
                ListingPriceHistory(
                    listing_id=listing.listing_id,
                    url=listing.url,
                    preco=adjusted_price,
                    condominio=listing.condominio,
                    moeda=listing.moeda or "BRL",
                    fonte=source,
                    observed_at=ts,
                )
            )

        self.session.add_all(history_objs)
        self.session.commit()
        return len(history_objs)
