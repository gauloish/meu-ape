"""Repository implementations for database entity access and persistence."""

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import GeocodingCache, Listing


def _safe_float(val: Any) -> Optional[float]:
    if val is None or pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    if val is None or pd.isna(val):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> Optional[str]:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


class GeocodingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, address: str) -> GeocodingCache | None:
        """Return the geocoded persisted address in database

        Args:
            address (str): Address whose geocoded version will be retrieved

        Returns:
            GeocodingCache | None: Geocoded address
        """
        return self.session.get(
            GeocodingCache,
            address,
        )

    def exists(self, address: str) -> bool:
        """Check if exists a geocoded version of given address in database

        Args:
            address (str): Address to be checked

        Returns:
            bool: `True` if the geocoded address is persisted
            in database. Otherwise, `False`
        """
        return self.get(address) is not None

    def add(self, geocoding: GeocodingCache) -> None:
        """Add a new geocoded address in the database

        Args:
            geocoding (GeocodingCache): New geocoded address to be
            added in the database
        """
        self.session.add(geocoding)

    def add_many(self, geocodings: Iterable[GeocodingCache]) -> None:
        """Add many geocoded addresses in the database

        Args:
            geocodings (Iterable[GeocodingCache]): A list of new
            geocoded addresses to be added in the database
        """
        self.session.add_all(geocodings)


class ListingRepository:
    """Repository managing property listing persistence and deduplication."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_ids(self) -> Set[str]:
        """Fetch set of all listing IDs currently stored in the database.

        Returns:
            Set of listing ID strings.
        """
        stmt = select(Listing.listing_id)
        results = self.session.scalars(stmt).all()
        return set(results)

    def get_existing_ids(self, listing_ids: Iterable[str]) -> Set[str]:

        """Query database for listing IDs that are already persisted.

        Args:
            listing_ids: Collection of listing IDs to check.

        Returns:
            Set of listing IDs present in the database.
        """
        ids_list = [str(i) for i in listing_ids if i and not pd.isna(i)]
        if not ids_list:
            return set()

        existing: Set[str] = set()
        chunk_size = 500
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i : i + chunk_size]
            stmt = select(Listing.listing_id).where(Listing.listing_id.in_(chunk))
            results = self.session.scalars(stmt).all()
            existing.update(results)
        return existing

    def add_many(self, records: List[Dict[str, Any]]) -> int:
        """Insert new listing records into database, ignoring already existing IDs.

        Args:
            records: List of parsed listing dictionaries.

        Returns:
            Count of newly inserted listings.
        """
        if not records:
            return 0

        # Deduplicate batch internally
        unique_records: Dict[str, Dict[str, Any]] = {}
        for r in records:
            raw_id = r.get("id") or r.get("listing_id")
            lid = _safe_str(raw_id)
            if lid and lid not in unique_records:
                unique_records[lid] = r

        if not unique_records:
            return 0

        existing_ids = self.get_existing_ids(unique_records.keys())
        new_records = [r for lid, r in unique_records.items() if lid not in existing_ids]

        if not new_records:
            return 0

        objs: List[Listing] = []
        for r in new_records:
            lid = _safe_str(r.get("id") or r.get("listing_id"))
            if not lid:
                continue

            raw_scraped = r.get("scraped_at")
            if isinstance(raw_scraped, str) and not pd.isna(raw_scraped):
                try:
                    scraped_dt = datetime.fromisoformat(raw_scraped)
                except (ValueError, TypeError):
                    scraped_dt = datetime.now(timezone.utc)
            elif isinstance(raw_scraped, datetime):
                scraped_dt = raw_scraped
            else:
                scraped_dt = datetime.now(timezone.utc)

            objs.append(
                Listing(
                    listing_id=lid,
                    titulo=_safe_str(r.get("titulo")),
                    tipo_imovel=_safe_str(r.get("tipo_imovel")),
                    url=_safe_str(r.get("url")),
                    preco=_safe_float(r.get("preco")),
                    moeda=_safe_str(r.get("moeda")),
                    condominio=_safe_float(r.get("condominio")),
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

        self.session.add_all(objs)
        self.session.commit()
        return len(objs)
