"""Suíte de testes unitários para a fábrica da engine do SQLAlchemy."""

import importlib

import pytest

# O pacote src.database reexporta o objeto `engine`, que sombreia o submódulo homônimo.
engine_module = importlib.import_module("src.database.engine")


@pytest.fixture
def captured_urls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Substitui create_engine para capturar a URL resolvida sem abrir conexões."""
    urls: list[str] = []

    def _fake_create_engine(url: str, **_kwargs):
        urls.append(url)
        return object()

    monkeypatch.setattr(engine_module, "create_engine", _fake_create_engine)
    return urls


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ],
)
def test_normalises_postgres_scheme(raw_url, expected, captured_urls, monkeypatch):
    """Valida a conversão das URLs do Postgres (Vercel/Neon) para o driver psycopg v3."""
    monkeypatch.setenv("DATABASE_URL", raw_url)
    engine_module._build_engine()
    assert captured_urls == [expected]


def test_falls_back_to_local_sqlite(captured_urls, monkeypatch, tmp_path):
    """Valida o fallback para SQLite local quando DATABASE_URL não está definida."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(engine_module, "PROJECT_ROOT", tmp_path)

    engine_module._build_engine()

    assert captured_urls[0].startswith(f"sqlite:///{tmp_path}")
