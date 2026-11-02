"""Suíte de testes unitários para os pipelines de coleta diária e carga em lote."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from src.database import ListingRepository
from src.pipeline import daily_scrape, load_csv
from tests.conftest import make_record


@pytest.fixture
def patched_db(
    monkeypatch: pytest.MonkeyPatch, db_engine, session_factory: sessionmaker[Session]
):
    """Aponta os pipelines para o banco SQLite em memória."""
    for module in (daily_scrape, load_csv):
        monkeypatch.setattr(module, "engine", db_engine)
        monkeypatch.setattr(module, "Session", session_factory)
    return session_factory


def _fake_scraper(records: list[dict], calls: list[dict]):
    """Cria um substituto de scrape_full_async que grava os registros fornecidos em data/raw."""

    async def _scrape(**kwargs) -> Path:
        calls.append(kwargs)
        path = Path("data/raw") / kwargs["output_filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if records:
            pd.DataFrame(records).to_csv(path, index=False)
        return path

    return _scrape


def test_daily_pipeline_persists_new_listings(workdir: Path, patched_db, monkeypatch):
    """Valida o fluxo completo: IDs conhecidos, coleta, deduplicação física e persistência."""
    with patched_db() as session:
        ListingRepository(session).add_many([make_record("antigo", rua="Rua 1")])

    calls: list[dict] = []
    records = [
        make_record("1"),
        make_record("2", fotos_urls="a"),  # mesmo imóvel físico que "1", menos completo
        make_record("3", rua="Avenida 85", preco=900000.0),
    ]
    monkeypatch.setattr(
        daily_scrape, "scrape_full_async", _fake_scraper(records, calls)
    )

    daily_scrape.run_daily_pipeline(concurrency=2, max_pages=5)

    assert calls[0]["known_ids"] == {"antigo"}
    assert calls[0]["concurrency"] == 2
    assert calls[0]["max_pages"] == 5
    with patched_db() as session:
        assert ListingRepository(session).get_all_ids() == {"antigo", "1", "3"}
    assert list((workdir / "data" / "processed").glob("zap_daily_*_dedup.csv"))


def test_daily_pipeline_dry_run_does_not_write(workdir: Path, patched_db, monkeypatch):
    """Valida que o modo dry-run não grava no banco."""
    monkeypatch.setattr(
        daily_scrape, "scrape_full_async", _fake_scraper([make_record("1")], [])
    )

    daily_scrape.run_daily_pipeline(dry_run=True)

    with patched_db() as session:
        assert ListingRepository(session).get_all_ids() == set()


def test_daily_pipeline_exits_when_nothing_scraped(
    workdir: Path, patched_db, monkeypatch
):
    """Valida a saída antecipada quando a coleta não produz arquivo."""
    monkeypatch.setattr(daily_scrape, "scrape_full_async", _fake_scraper([], []))

    daily_scrape.run_daily_pipeline()

    assert not (workdir / "data" / "processed").exists()


def test_load_csv_inserts_in_chunks(tmp_path: Path, patched_db):
    """Valida a carga em lote de um CSV existente, ignorando IDs repetidos."""
    csv_path = tmp_path / "dataset.csv"
    ids = ["2902564623", "2835720338", "2857048455", "2771234567", "2700000001"]
    pd.DataFrame([make_record(i) for i in ids] + [make_record(ids[0])]).to_csv(
        csv_path, index=False
    )

    load_csv.load_csv_to_db(csv_path, chunk_size=2)

    with patched_db() as session:
        assert ListingRepository(session).get_all_ids() == set(ids)


def test_load_csv_missing_file(tmp_path: Path, patched_db):
    """Valida que um arquivo inexistente não gera exceção."""
    load_csv.load_csv_to_db(tmp_path / "inexistente.csv")
