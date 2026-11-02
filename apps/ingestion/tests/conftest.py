"""Configurações globais e fixtures para a suíte de testes da ingestion."""

import os

# Garante que a engine criada na importação de src.database nunca aponte para o banco real do .env.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.base import Base


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    """Retorna uma engine SQLite em memória compartilhada entre conexões, com o schema criado."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    """Retorna uma fábrica de sessões vinculada à engine de testes."""
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session(
    session_factory: sessionmaker[Session],
) -> Generator[Session, None, None]:
    """Retorna uma sessão ativa do SQLAlchemy sobre o banco em memória."""
    with session_factory() as session:
        yield session


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Muda o diretório de trabalho para um diretório temporário (os módulos usam caminhos relativos em data/)."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_record(listing_id: str, **overrides: Any) -> dict[str, Any]:
    """Constrói um registro de anúncio no formato produzido por parse_item."""
    record: dict[str, Any] = {
        "id": listing_id,
        "titulo": "Apartamento com 3 quartos à venda, 90m² em Setor Bueno, Goiânia",
        "tipo_imovel": "Apartment",
        "url": f"https://www.zapimoveis.com.br/imovel/{listing_id}/",
        "preco": 650000.0,
        "moeda": "BRL",
        "condominio": 550.0,
        "area_m2": 90.0,
        "quartos": 3,
        "banheiros": 2,
        "vagas": 2,
        "bairro": "Setor Bueno",
        "rua": "Rua T-55",
        "cidade": "Goiânia",
        "estado": "GO",
        "pais": "BR",
        "aceita_pets": "true",
        "comodidades": "Piscina, Academia",
        "fotos_urls": "https://img/1.jpg, https://img/2.jpg",
        "descricao_completa": "Ótimo apartamento.",
        "data_publicacao": "2026-10-30T10:00:00Z",
        "data_modificacao": "2026-10-31T10:00:00Z",
        "scraped_at": "2026-11-01T12:00:00+00:00",
    }
    record.update(overrides)
    return record
