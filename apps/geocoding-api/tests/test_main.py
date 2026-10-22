"""Testes unitários para inicialização da aplicação FastAPI e lifespan da geocoding-api."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import app, lifespan


def test_app_metadata():
    """Valida título, versão e inclusão dos roteadores na aplicação FastAPI."""
    assert app.title == "API de Geocodificação em Cache"
    assert app.version == "1.1.0"
    route_paths = list(app.openapi()["paths"].keys())
    assert "/health" in route_paths
    assert "/geocoding/search" in route_paths
    assert "/geocoding/search/batch" in route_paths
    assert "/geocoding/reverse" in route_paths
    assert "/geocoding/reverse/batch" in route_paths


def test_lifespan_lifecycle_and_db_resilience(
    monkeypatch: pytest.MonkeyPatch,
):
    """Valida inicialização e encerramento dos recursos no lifespan tratando indisponibilidade de banco."""

    async def _test():
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.side_effect = RuntimeError("PostgreSQL offline")
        mock_ctx.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_ctx
        mock_engine.dispose = AsyncMock()

        monkeypatch.setattr("src.main.engine", mock_engine)

        async with lifespan(app):
            assert hasattr(app.state, "http_client")
            assert app.state.http_client is not None

        mock_engine.dispose.assert_called_once()

    asyncio.run(_test())
