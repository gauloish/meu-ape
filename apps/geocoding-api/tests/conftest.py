"""Configurações globais e fixtures para a suíte de testes da geocoding-api."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from src.dependencies import get_db, get_http_client
from src.main import app


@pytest.fixture(autouse=True)
def mock_engine_lifespan(monkeypatch: pytest.MonkeyPatch):
    """Evita tentativas de conexão física ao PostgreSQL durante o lifespan da aplicação nos testes."""
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    mock_engine.dispose = AsyncMock()

    monkeypatch.setattr("src.main.engine", mock_engine)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Retorna uma sessão mockada do SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Retorna um cliente HTTP mockado (httpx.AsyncClient)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value=[
            {
                "lat": "-16.6868",
                "lon": "-49.2648",
                "place_id": "123456",
                "display_name": "Avenida Anhanguera, Setor Central, Goiânia, GO",
            }
        ]
    )
    client.get = AsyncMock(return_value=resp)
    return client


@pytest.fixture
def client(
    mock_db_session: AsyncMock, mock_http_client: AsyncMock
) -> Generator[TestClient, None, None]:
    """Retorna um TestClient do FastAPI com as dependências de banco e HTTP sobrescritas."""

    async def _override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    def _override_get_http_client() -> AsyncMock:
        return mock_http_client

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_http_client] = _override_get_http_client

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
