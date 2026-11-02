"""Asynchronous Zap Imóveis scraper orchestration module.

Drives asynchronous page gathering over partitioned search spaces using asyncio and
AsyncHttpClient, delegating parsing to zap_parser and storage/resumption to CheckpointStore.
"""

import asyncio
import json
import logging
import random
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio

from src.data.checkpoint import CheckpointStore
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
from src.scraping.zap_parser import normalize_url, parse_item

logger = logging.getLogger(__name__)


def build_search_url(
    path: str,
    page: int,
    price_min: int | None,
    price_max: int | None,
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


def make_partition_key(
    search_path: str, price_min: int | None, price_max: int | None
) -> str:
    """Construct a deterministic key identifying a category and price partition."""
    return f"{search_path.strip('/')}:{price_min}:{price_max}"


def extract_listings_from_html(html: str) -> list[dict]:
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
        except Exception:  # noqa: BLE001, S110
            pass
    return listings


def _listing_matches_date(record: dict, target_date: date) -> bool:
    """Return True if the listing was published or modified on target_date.

    Tries ``data_publicacao`` first, then ``data_modificacao`` as fallback.
    Accepts ISO 8601 strings (with or without time component).

    Args:
        record: Parsed listing dictionary containing date fields.
        target_date: The date to match against.

    Returns:
        True if the record's date matches target_date, False otherwise
        (including when no date field is present).
    """
    for field in ("data_publicacao", "data_modificacao"):
        raw = record.get(field)
        if not raw:
            continue
        try:
            parsed = date.fromisoformat(str(raw)[:10])
            return parsed == target_date
        except (ValueError, TypeError):
            continue
    return False


async def scrape_partition(
    client: AsyncHttpClient,
    store: CheckpointStore,
    lock: asyncio.Lock,
    search_path: str,
    price_min: int | None,
    price_max: int | None,
    known_ids: set[str] | None = None,
    max_pages: int = MAX_PAGES_PER_PARTITION,
    known_urls: set[str] | None = None,
) -> None:
    """Asynchronously scrape pagination for a single category and price range partition.

    Supports resuming from the last processed page recorded in ``store``.

    Args:
        client: Asynchronous HTTP client instance.
        store: Thread-safe checkpoint persistence store.
        lock: Asyncio lock for synchronizing store updates.
        search_path: URL path for the category and city.
        price_min: Lower price bound.
        price_max: Upper price bound.
        known_ids: Set of listing IDs already in the database. When set, stops pagination
                   if all listings on a page are already known.
        max_pages: Upper limit of pages to scrape per partition.
        known_urls: Set of normalised listing URLs already in the database.
    """
    label = search_path.split("/")[-1]
    partition_key = make_partition_key(search_path, price_min, price_max)

    if store.is_partition_completed(partition_key):
        logger.debug(
            "[%s] Partition %s already completed — skipping.", label, partition_key
        )
        return

    start_page = store.get_resume_page(partition_key)

    for page in range(start_page, max_pages + 1):
        url = build_search_url(search_path, page, price_min, price_max)
        html = await client.get(url, label=label)
        listings = extract_listings_from_html(html)

        if not listings:
            async with lock:
                store.record_progress(partition_key, page, completed=True)
            break

        if known_ids or known_urls:
            page_ids = {str(item.get("id")) for item in listings if item.get("id")}
            page_urls = {
                norm
                for item in listings
                if item.get("url") and (norm := normalize_url(str(item.get("url"))))
            }
            new_ids = page_ids - (known_ids or set())
            new_urls = page_urls - (known_urls or set())
            all_ids_known = bool(known_ids) and not new_ids
            all_urls_known = bool(known_urls) and bool(page_urls) and not new_urls
            if (all_ids_known or all_urls_known) and page > 1:
                logger.info(
                    "[%s] Page %d: all listings already in DB — stopping partition.",
                    label,
                    page,
                )
                async with lock:
                    store.record_progress(partition_key, page, completed=True)
                break

        async with lock:
            new_count = store.add_many(listings)
            store.record_progress(partition_key, page, completed=(page >= max_pages))
            if store.buffer_full:
                await store.flush_async(force=True)

        if new_count:
            logger.info(
                "[%s] Page %d: +%d new listings (Total: %d)",
                label,
                page,
                new_count,
                store.total_seen,
            )
        else:
            logger.info(
                "[%s] Page %d: %d listings already existing in store.",
                label,
                page,
                len(listings),
            )

        await asyncio.sleep(random.uniform(1.5, 3.0))


async def scrape_full_async(
    city_slug: str = DEFAULT_CITY_SLUG,
    output_filename: str = DEFAULT_OUTPUT_FILENAME,
    concurrency: int = DEFAULT_CONCURRENCY,
    known_ids: set[str] | None = None,
    max_pages: int = MAX_PAGES_PER_PARTITION,
    known_urls: set[str] | None = None,
) -> Path:
    """Execute asynchronous extraction across all property categories and price partitions.

    Args:
        city_slug: Target city and state slug string.
        output_filename: Destination CSV filename.
        concurrency: Semaphore concurrency limit.
        known_ids: Pre-loaded set of existing listing IDs for early termination.
        max_pages: Page limit per partition (default 50).
        known_urls: Pre-loaded set of existing normalised listing URLs.

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
        "Starting asynchronous extractor (%d concurrency limit | %d partitions | %d known DB IDs)",
        concurrency,
        len(partitions),
        len(known_ids) if known_ids else 0,
    )

    async with AsyncHttpClient(semaphore=semaphore) as client:
        tasks = [
            scrape_partition(
                client=client,
                store=store,
                lock=lock,
                search_path=path,
                price_min=p_min,
                price_max=p_max,
                known_ids=known_ids,
                max_pages=max_pages,
                known_urls=known_urls,
            )
            for path, p_min, p_max in partitions
        ]
        await tqdm_asyncio.gather(*tasks, desc="Async Progress")

        if client.blocked_count > 0 or client.rate_limited_count > 0:
            logger.warning(
                "Scraper encountered edge blocks during run: %d HTTP 403 responses, %d HTTP 429 responses.",
                client.blocked_count,
                client.rate_limited_count,
            )

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
        if arg.startswith(("--concurrency=", "-c=")):
            concurrency = int(arg.split("=")[1])

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(scrape_full_async(concurrency=concurrency))


if __name__ == "__main__":
    main()
