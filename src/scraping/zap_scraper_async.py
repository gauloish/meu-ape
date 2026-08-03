"""Asynchronous Zap Imóveis scraper orchestration module.

Drives asynchronous page gathering over partitioned search spaces using asyncio and
curl_cffi AsyncSession, delegating parsing to zap_parser and storage to CheckpointStore.
"""

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

from src.scraping.config import (
    BASE_URL,
    CHECKPOINT_BUFFER_SIZE,
    DEFAULT_CITY_SLUG,
    DEFAULT_CONCURRENCY,
    DEFAULT_OUTPUT_FILENAME,
    MAX_PAGES_PER_PARTITION,
    PRICE_RANGES,
    PROPERTY_CATEGORIES,
)
from src.scraping.http_client import AsyncHttpClient
from src.scraping.zap_parser import parse_item
from src.data.checkpoint import CheckpointStore

logger = logging.getLogger(__name__)


def build_search_url(
    path: str,
    page: int,
    price_min: Optional[int],
    price_max: Optional[int],
) -> str:
    """Build a search URL formatted for Zap Imóveis pagination and price filtering.

    Args:
        path: Category and location search path segment.
        page: Target page number.
        price_min: Minimum price bound filter.
        price_max: Maximum price bound filter.

    Returns:
        Formatted target URL string.
    """
    params = [f"pagina={page}"]
    if price_min is not None:
        params.append(f"preco-de={price_min}")
    if price_max is not None:
        params.append(f"preco-ate={price_max}")
    return f"{BASE_URL}/{path.strip('/')}/?{'&'.join(params)}"


def extract_listings_from_html(html: str) -> List[dict]:
    """Parse JSON-LD script elements from raw HTML response body.

    Args:
        html: Raw HTML content string.

    Returns:
        List of parsed listing dictionaries.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for element in data.get("itemListElement", []):
                    raw_item = element.get("item")
                    if raw_item and isinstance(raw_item, dict):
                        listings.append(parse_item(raw_item))
        except Exception:
            pass
    return listings


async def scrape_partition(
    client: AsyncHttpClient,
    store: CheckpointStore,
    lock: asyncio.Lock,
    search_path: str,
    price_min: Optional[int],
    price_max: Optional[int],
) -> None:
    """Asynchronously scrape pagination for a single category and price range partition.

    Args:
        client: Asynchronous HTTP client instance.
        store: Thread-safe checkpoint persistence store.
        lock: Asyncio lock for synchronizing store updates.
        search_path: URL path for the category and city.
        price_min: Lower price bound.
        price_max: Upper price bound.
    """
    label = search_path.split("/")[-1]

    for page in range(1, MAX_PAGES_PER_PARTITION + 1):
        url = build_search_url(search_path, page, price_min, price_max)
        html = await client.get(url, label=label)
        listings = extract_listings_from_html(html)

        if not listings:
            break

        async with lock:
            new_count = store.add_many(listings)
            if store.buffer_full:
                await store.flush_async(force=True)

        if new_count:
            logger.info("[%s] Page %d: +%d new listings (Total: %d)", label, page, new_count, store.total_seen)
        else:
            logger.info("[%s] Page %d: %d listings already existing.", label, page, len(listings))

        await asyncio.sleep(random.uniform(1.5, 3.0))


async def scrape_full_async(
    city_slug: str = DEFAULT_CITY_SLUG,
    output_filename: str = DEFAULT_OUTPUT_FILENAME,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> Path:
    """Execute asynchronous extraction across all property categories and price partitions.

    Args:
        city_slug: Target city and state slug string.
        output_filename: Destination CSV filename.
        concurrency: Semaphore concurrency limit.

    Returns:
        Path to the output CSV file.
    """
    output_path = Path("data/raw") / output_filename
    store = CheckpointStore(output_path=output_path, buffer_size=CHECKPOINT_BUFFER_SIZE)
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()

    partitions = [
        (f"venda/{cat}/{city_slug}", p_min, p_max)
        for cat in PROPERTY_CATEGORIES
        for p_min, p_max in PRICE_RANGES
    ]

    logger.info(
        "Starting asynchronous extractor (%d concurrency limit | %d partitions)",
        concurrency,
        len(partitions),
    )

    async with AsyncHttpClient(semaphore=semaphore) as client:
        tasks = [
            scrape_partition(client, store, lock, path, p_min, p_max)
            for path, p_min, p_max in partitions
        ]
        await tqdm_asyncio.gather(*tasks, desc="Async Progress")

    await store.flush_async(force=True)
    logger.info(
        "Async extraction completed: %d total unique listings saved to %s",
        store.total_seen,
        output_path.resolve(),
    )
    return output_path


def main() -> None:
    """CLI entry point for running the async scraper module directly."""
    import sys
    concurrency = DEFAULT_CONCURRENCY
    for arg in sys.argv[1:]:
        if arg.startswith("--concurrency=") or arg.startswith("-c="):
            concurrency = int(arg.split("=")[1])

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(scrape_full_async(concurrency=concurrency))


if __name__ == "__main__":
    main()
