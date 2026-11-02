"""Suíte de testes unitários para os clientes HTTP com retentativas do scraper."""

import asyncio
from types import SimpleNamespace

import pytest

from src.scraping import http_client
from src.scraping.http_client import AsyncHttpClient, SyncHttpClient


def _response(status_code: int, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(status_code=status_code, text=text)


class FakeAsyncSession:
    """Sessão assíncrona falsa que devolve respostas em sequência."""

    def __init__(self, responses: list) -> None:
        self.responses = list(responses)
        self.cookies: dict = {}
        self.closed = False

    async def get(self, url: str, **_kwargs):
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def close(self) -> None:
        self.closed = True


class FakeSyncSession:
    """Sessão síncrona falsa que devolve respostas em sequência."""

    def __init__(self, responses: list) -> None:
        self.responses = responses

    def get(self, url: str, **_kwargs):
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elimina as esperas de backoff para manter os testes rápidos."""

    async def _async_sleep(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(http_client.asyncio, "sleep", _async_sleep)
    monkeypatch.setattr(http_client.time, "sleep", lambda *_args: None)


def _async_client(
    session: FakeAsyncSession, monkeypatch: pytest.MonkeyPatch
) -> tuple[AsyncHttpClient, list]:
    """Cria um AsyncHttpClient com sessão injetada e registra os resets de sessão."""
    client = AsyncHttpClient(semaphore=asyncio.Semaphore(1))
    client._session = session  # ty: ignore[invalid-assignment]
    resets: list = []

    async def _fake_reset() -> None:
        resets.append(True)

    monkeypatch.setattr(client, "_reset_session", _fake_reset)
    return client, resets


def test_async_get_returns_body_on_200(monkeypatch):
    """Valida o retorno do corpo da resposta em caso de sucesso."""
    client, _ = _async_client(FakeAsyncSession([_response(200, "ok")]), monkeypatch)
    assert asyncio.run(client.get("https://x")) == "ok"


def test_async_get_returns_empty_on_404(monkeypatch):
    """Valida que páginas inexistentes encerram sem retentativas."""
    session = FakeAsyncSession([_response(404), _response(200, "nunca")])
    client, _ = _async_client(session, monkeypatch)

    assert asyncio.run(client.get("https://x")) == ""
    assert len(session.responses) == 1


def test_async_get_retries_after_rate_limit(monkeypatch):
    """Valida a retentativa após HTTP 429."""
    client, _ = _async_client(
        FakeAsyncSession([_response(429), _response(200, "ok")]), monkeypatch
    )
    assert asyncio.run(client.get("https://x")) == "ok"


def test_async_get_resets_session_on_403(monkeypatch):
    """Valida a recriação da sessão após HTTP 403."""
    client, resets = _async_client(
        FakeAsyncSession([_response(403), _response(200, "ok")]), monkeypatch
    )

    assert asyncio.run(client.get("https://x")) == "ok"
    assert resets == [True]


def test_async_get_gives_up_after_max_retries(monkeypatch):
    """Valida a desistência após esgotar as retentativas em erros de conexão."""
    session = FakeAsyncSession([ConnectionError("falha")] * AsyncHttpClient.MAX_RETRIES)
    client, resets = _async_client(session, monkeypatch)

    assert asyncio.run(client.get("https://x")) == ""
    assert len(resets) == AsyncHttpClient.MAX_RETRIES - 1


def test_async_get_gives_up_on_persistent_server_error(monkeypatch):
    """Valida a desistência após respostas 5xx consecutivas."""
    client, _ = _async_client(
        FakeAsyncSession([_response(500)] * AsyncHttpClient.MAX_RETRIES), monkeypatch
    )
    assert asyncio.run(client.get("https://x")) == ""


def test_async_context_manager_warms_and_closes(monkeypatch):
    """Valida o aquecimento da sessão na entrada e o fechamento na saída do contexto."""
    session = FakeAsyncSession([_response(200, "home")])
    monkeypatch.setattr(http_client, "AsyncSession", lambda **_kwargs: session)

    async def _run() -> AsyncHttpClient:
        async with AsyncHttpClient(semaphore=asyncio.Semaphore(1)) as client:
            return client

    client = asyncio.run(_run())
    assert client._warmed
    assert session.closed


def test_sync_get_retries_and_rebuilds_session(monkeypatch):
    """Valida a retentativa síncrona com recriação de sessão a cada nova tentativa."""
    responses = [_response(429), _response(403), _response(200, "ok")]
    built: list = []

    def _build(self):
        built.append(True)
        return FakeSyncSession(responses)

    monkeypatch.setattr(http_client, "HAS_CURL_CFFI", True)
    monkeypatch.setattr(SyncHttpClient, "_build_session", _build)

    assert SyncHttpClient().get("https://x") == "ok"
    assert len(built) == 3


def test_sync_get_returns_empty_on_410_and_exceptions(monkeypatch):
    """Valida o retorno vazio para recursos removidos e para falhas de conexão persistentes."""
    monkeypatch.setattr(http_client, "HAS_CURL_CFFI", True)

    monkeypatch.setattr(
        SyncHttpClient, "_build_session", lambda self: FakeSyncSession([_response(410)])
    )
    assert SyncHttpClient().get("https://x") == ""

    errors = [OSError("falha")] * SyncHttpClient.MAX_RETRIES
    monkeypatch.setattr(
        SyncHttpClient, "_build_session", lambda self: FakeSyncSession(errors)
    )
    assert SyncHttpClient().get("https://x") == ""
