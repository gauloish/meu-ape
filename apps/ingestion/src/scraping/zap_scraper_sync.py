"""Synchronous Zap Imóveis scraper orchestration module.

Orchestrates multi-threaded pagination and partitioning over property categories and
price ranges, delegating HTTP fetching to SyncHttpClient and item parsing to zap_parser.
"""

import json
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from tqdm import tqdm

from src.scraping.config import (
    BASE_URL,
    DEFAULT_BUSINESS_TYPE,
    DEFAULT_CITY_SLUG,
    DEFAULT_OUTPUT_FILENAME,
    MAX_PAGES_PER_PARTITION,
    PRICE_RANGES,
    PROPERTY_CATEGORIES,
)
from src.scraping.http_client import SyncHttpClient
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


def scrape_partition(
    client: SyncHttpClient,
    store: CheckpointStore,
    lock: threading.Lock,
    search_path: str,
    price_min: Optional[int],
    price_max: Optional[int],
    delay_range: Tuple[float, float] = (3.0, 6.0),
) -> None:
    """Iterate over pagination for a single category and price range partition.

    Args:
        client: Synchronous HTTP client instance.
        store: Thread-safe checkpoint persistence store.
        lock: Threading lock for synchronizing store updates.
        search_path: URL path for the category and city.
        price_min: Lower price bound.
        price_max: Upper price bound.
        delay_range: Tuple of minimum and maximum delay in seconds between requests.
    """
    label = search_path.split("/")[-1]

    for page in range(1, MAX_PAGES_PER_PARTITION + 1):
        url = build_search_url(search_path, page, price_min, price_max)
        html = client.get(url)
        listings = extract_listings_from_html(html)

        if not listings:
            break

        with lock:
            new_count = store.add_many(listings)
            if store.buffer_full:
                store.flush_sync()

        if new_count:
            logger.info("[%s] Page %d: +%d new listings (Total: %d)", label, page, new_count, store.total_seen)
        else:
            logger.info("[%s] Page %d: %d listings already existing.", label, page, len(listings))

        time.sleep(random.uniform(*delay_range))


def scrape_full(
    city_slug: str = DEFAULT_CITY_SLUG,
    business_type: str = DEFAULT_BUSINESS_TYPE,
    output_filename: str = DEFAULT_OUTPUT_FILENAME,
    delay_range: Tuple[float, float] = (3.0, 6.0),
    max_workers: int = 1,
) -> Path:
    """Execute full extraction across all property categories and price partitions.

    Args:
        city_slug: Target city and state slug string.
        business_type: Transaction type slug (e.g., 'venda').
        output_filename: Destination CSV filename.
        delay_range: Politeness delay range between page requests.
        max_workers: Thread pool concurrency limit.

    Returns:
        Path to the output CSV file.
    """
    output_path = Path("data/raw") / output_filename
    store = CheckpointStore(output_path=output_path)
    client = SyncHttpClient()
    lock = threading.Lock()

    partitions: List[Tuple] = [
        (f"{business_type}/{cat}/{city_slug}", p_min, p_max)
        for cat in PROPERTY_CATEGORIES
        for p_min, p_max in PRICE_RANGES
    ]

    logger.info(
        "Starting synchronous extractor (%d workers | %d partitions)",
        max_workers,
        len(partitions),
    )

    with tqdm(total=len(partitions), desc="Partition Progress") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    scrape_partition, client, store, lock, path, p_min, p_max, delay_range
                ): path
                for path, p_min, p_max in partitions
            }
            for future in as_completed(futures):
                pbar.update(1)
                try:
                    future.result()
                except Exception as exc:
                    logger.warning("Error in partition %s: %s", futures[future], exc)

    with lock:
        store.flush_sync()

    logger.info(
        "Extraction completed: %d total unique listings saved to %s",
        store.total_seen,
        output_path.resolve(),
    )
    return output_path
