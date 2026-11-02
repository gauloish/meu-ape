"""Suíte de testes unitários para a orquestração dos scrapers do Zap Imóveis."""

import asyncio
import json
from datetime import date
from pathlib import Path

from src.data.checkpoint import CheckpointStore
from src.scraping import zap_scraper_async, zap_scraper_sync
from src.scraping.http_client import AsyncHttpClient
from src.scraping.zap_scraper_async import (
    _listing_matches_date,
    build_search_url,
    extract_listings_from_html,
    scrape_partition,
)


def _html_page(*listing_ids: str) -> str:
    """Gera uma página HTML com um bloco JSON-LD do tipo ItemList."""
    payload = {
        "@type": "ItemList",
        "itemListElement": [
            {"item": {"@id": lid, "name": f"Imóvel {lid}"}} for lid in listing_ids
        ],
    }
    return (
        "<html><head>"
        '<script type="application/ld+json">{"@type": "Organization"}</script>'
        '<script type="application/ld+json">not json</script>'
        f'<script type="application/ld+json">{json.dumps(payload)}</script>'
        "</head></html>"
    )


class FakeAsyncClient(AsyncHttpClient):
    """Cliente HTTP assíncrono falso que devolve páginas pré-definidas por número de página."""

    def __init__(self, pages: dict[int, str]) -> None:
        super().__init__(semaphore=asyncio.Semaphore(1))
        self.pages = pages
        self.requested: list[str] = []

    async def get(self, url: str, label: str = "") -> str:
        self.requested.append(url)
        page = int(url.split("pagina=")[1].split("&")[0])
        return self.pages.get(page, "")


async def _no_sleep(*_args, **_kwargs) -> None:
    return None


def test_build_search_url_with_price_bounds():
    """Valida a montagem da URL com paginação e filtros de preço."""
    url = build_search_url("/venda/apartamentos/go+goiania/", 2, 100_000, 200_000)
    assert url == (
        "https://www.zapimoveis.com.br/venda/apartamentos/go+goiania/"
        "?pagina=2&preco-de=100000&preco-ate=200000"
    )


def test_build_search_url_without_upper_bound():
    """Valida a omissão do filtro de preço máximo na última faixa."""
    url = build_search_url("venda/casas/go+goiania", 1, 25_000_000, None)
    assert url.endswith("?pagina=1&preco-de=25000000")


def test_sync_and_async_url_builders_are_equivalent():
    """Valida que os scrapers síncrono e assíncrono geram URLs idênticas."""
    args = ("venda/casas/go+goiania", 3, None, 500_000)
    assert zap_scraper_sync.build_search_url(
        *args
    ) == zap_scraper_async.build_search_url(*args)


def test_extract_listings_from_html_ignores_other_blocks():
    """Valida que apenas blocos ItemList válidos geram anúncios."""
    listings = extract_listings_from_html(_html_page("1", "2"))
    assert [item["id"] for item in listings] == ["1", "2"]


def test_extract_listings_from_html_empty():
    """Valida o retorno vazio para HTML vazio ou sem JSON-LD."""
    assert extract_listings_from_html("") == []
    assert extract_listings_from_html("<html></html>") == []
    assert zap_scraper_sync.extract_listings_from_html("") == []


def test_listing_matches_date():
    """Valida a comparação de data de publicação/modificação com a data alvo."""
    target = date(2026, 11, 1)
    assert _listing_matches_date({"data_publicacao": "2026-11-01T08:00:00Z"}, target)
    assert _listing_matches_date(
        {"data_publicacao": "lixo", "data_modificacao": "2026-11-01"}, target
    )
    assert not _listing_matches_date({"data_publicacao": "2026-10-01"}, target)
    assert not _listing_matches_date({}, target)


def test_scrape_partition_stops_on_empty_page(workdir: Path, monkeypatch):
    """Valida que a paginação para quando uma página não retorna anúncios."""
    monkeypatch.setattr(zap_scraper_async.asyncio, "sleep", _no_sleep)
    client = FakeAsyncClient({1: _html_page("1", "2"), 2: _html_page("3")})
    store = CheckpointStore(output_path=workdir / "out.csv", buffer_size=100)

    asyncio.run(
        scrape_partition(
            client,
            store,
            asyncio.Lock(),
            "venda/casas/go+goiania",
            None,
            None,
            max_pages=10,
        )
    )

    assert len(client.requested) == 3
    assert store.seen_ids == {"1", "2", "3"}


def test_scrape_partition_stops_when_page_is_fully_known(workdir: Path, monkeypatch):
    """Valida a interrupção antecipada quando todos os anúncios da página já existem no banco."""
    monkeypatch.setattr(zap_scraper_async.asyncio, "sleep", _no_sleep)
    client = FakeAsyncClient(
        {1: _html_page("1"), 2: _html_page("2"), 3: _html_page("3")}
    )
    store = CheckpointStore(output_path=workdir / "out.csv", buffer_size=100)

    asyncio.run(
        scrape_partition(
            client,
            store,
            asyncio.Lock(),
            "venda/casas/go+goiania",
            None,
            None,
            known_ids={"1", "2"},
            max_pages=10,
        )
    )

    assert len(client.requested) == 2
    assert store.seen_ids == {"1"}


def test_scrape_partition_respects_max_pages(workdir: Path, monkeypatch):
    """Valida o limite de páginas por partição."""
    monkeypatch.setattr(zap_scraper_async.asyncio, "sleep", _no_sleep)
    client = FakeAsyncClient({p: _html_page(str(p)) for p in range(1, 20)})
    store = CheckpointStore(output_path=workdir / "out.csv", buffer_size=100)

    asyncio.run(
        scrape_partition(
            client,
            store,
            asyncio.Lock(),
            "venda/casas/go+goiania",
            None,
            None,
            max_pages=3,
        )
    )

    assert len(client.requested) == 3
