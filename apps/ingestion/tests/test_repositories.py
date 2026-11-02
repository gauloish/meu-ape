"""Suíte de testes unitários para o repositório de anúncios (ListingRepository)."""

from datetime import datetime
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Listing
from src.database.repositories import (
    ListingRepository,
    _safe_float,
    _safe_int,
    _safe_str,
)
from tests.conftest import make_record


def test_add_many_inserts_and_converts_types(db_session: Session):
    """Valida a inserção e a conversão de tipos dos campos do anúncio."""
    repo = ListingRepository(db_session)

    inserted = repo.add_many(
        [make_record("1", quartos="3.0", preco="650000", rua="  ")]
    )

    assert inserted == 1
    listing = db_session.get(Listing, "1")
    assert listing is not None
    assert listing.quartos == 3
    assert listing.preco == 650000.0
    assert listing.rua is None
    assert listing.scraped_at is not None
    assert listing.scraped_at.year == 2026


def test_add_many_skips_existing_and_batch_duplicates(db_session: Session):
    """Valida que IDs já persistidos ou repetidos no lote não são inseridos novamente."""
    repo = ListingRepository(db_session)
    repo.add_many([make_record("1")])

    inserted = repo.add_many(
        [make_record("1"), make_record("2"), make_record("2"), make_record("")]
    )

    assert inserted == 1
    assert repo.get_all_ids() == {"1", "2"}


def test_add_many_accepts_listing_id_key(db_session: Session):
    """Valida o suporte a registros vindos do banco, com a chave listing_id."""
    record = make_record("x")
    record["listing_id"] = record.pop("id")

    assert ListingRepository(db_session).add_many([record]) == 1


def test_add_many_handles_nan_and_invalid_scraped_at(db_session: Session):
    """Valida que NaN vira NULL e que scraped_at inválido recebe o horário atual."""
    repo = ListingRepository(db_session)

    repo.add_many(
        [make_record("1", condominio=np.nan, bairro=np.nan, scraped_at="ontem")]
    )
    repo.add_many([make_record("2", scraped_at=datetime(2026, 1, 1))])

    first = db_session.get(Listing, "1")
    assert first is not None
    assert first.condominio is None
    assert first.bairro is None
    assert first.scraped_at is not None
    second = db_session.get(Listing, "2")
    assert second is not None
    assert second.scraped_at == datetime(2026, 1, 1)


def test_add_many_empty(db_session: Session):
    """Valida que lotes vazios não tocam o banco."""
    assert ListingRepository(db_session).add_many([]) == 0
    assert db_session.scalars(select(Listing)).all() == []


def test_get_existing_ids_chunks_large_queries(db_session: Session):
    """Valida a consulta de IDs existentes em lotes maiores que o tamanho do chunk."""
    repo = ListingRepository(db_session)
    repo.add_many([make_record(str(i)) for i in range(0, 1200, 2)])

    ids: list[Any] = [str(i) for i in range(1200)] + [None, np.nan]
    existing = repo.get_existing_ids(ids)

    assert len(existing) == 600
    assert repo.get_existing_ids([]) == set()


def test_safe_converters():
    """Valida as funções auxiliares de conversão segura."""
    assert _safe_float("1.5") == 1.5
    assert _safe_float("abc") is None
    assert _safe_float(np.nan) is None
    assert _safe_int("2.0") == 2
    assert _safe_int("abc") is None
    assert _safe_int(None) is None
    assert _safe_str(" Bueno ") == "Bueno"
    assert _safe_str("") is None
    assert _safe_str(np.nan) is None
