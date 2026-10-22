"""Testes unitários para injeção de dependências (dependencies.py) na geocoding-api."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.dependencies import get_db, get_http_client


def test_get_http_client_from_request():
    """Valida que get_http_client extrai a instância AsyncClient de app.state."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    request = MagicMock()
    request.app.state.http_client = mock_client

    client = get_http_client(request)
    assert client is mock_client


def test_get_db_yields_session_and_handles_exception(monkeypatch):
    """Valida que get_db abre sessão e executa rollback em caso de exceção."""

    async def _test():
        mock_session = AsyncMock()
        mock_session_local = MagicMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session_local.return_value.__aexit__.return_value = None

        monkeypatch.setattr(
            "src.dependencies.AsyncSessionLocal",
            mock_session_local,
        )

        gen = get_db()
        session = await anext(gen)
        assert session is mock_session

        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("Erro simulado na transação"))

        mock_session.rollback.assert_called_once()

    asyncio.run(_test())
