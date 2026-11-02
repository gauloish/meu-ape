"""Scrapy spider module for structured JSON-LD listing extraction.

Implements a Scrapy spider that respects ``robots.txt`` and rate limits, parses
public JSON-LD ``ItemList`` payloads, supports partition-level resumption via
``CheckpointStore``, and records transport/WAF block events without anti-bot evasion.
"""

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import scrapy
from scrapy.http import Response

from src.data.checkpoint import CheckpointStore
from src.scraping.config import (
    CHECKPOINT_BUFFER_SIZE,
    DEFAULT_BUSINESS_TYPE,
    DEFAULT_CITY_SLUG,
    DEFAULT_HEADERS,
    DEFAULT_OUTPUT_FILENAME,
    MAX_PAGES_PER_PARTITION,
    PRICE_RANGES,
    PROPERTY_CATEGORIES,
    PriceRange,
)
from src.scraping.zap_parser import inspect_html_structure, normalize_url
from src.scraping.zap_scraper_async import (
    build_search_url,
    extract_listings_from_html,
    make_partition_key,
)

logger = logging.getLogger(__name__)


class ZapListingSpider(scrapy.Spider):
    """Scrapy spider for extracting JSON-LD real estate listings with resumption support."""

    name = "zap_goiania"

    custom_settings: dict[Any, Any] | None = {  # noqa: RUF012
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_MAX_DELAY": 15.0,
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 2.0,
        "DEFAULT_REQUEST_HEADERS": DEFAULT_HEADERS,
        "HTTPERROR_ALLOWED_CODES": [403, 404, 410, 429],
        "LOG_ENABLED": False,
    }

    def __init__(
        self,
        store: CheckpointStore,
        city_slug: str = DEFAULT_CITY_SLUG,
        business_type: str = DEFAULT_BUSINESS_TYPE,
        categories: list[str] | None = None,
        price_ranges: list[PriceRange] | None = None,
        max_pages: int = MAX_PAGES_PER_PARTITION,
        known_ids: set[str] | None = None,
        known_urls: set[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the Scrapy spider with partition and checkpoint configuration.

        Args:
            store: CheckpointStore instance for incremental persistence and resumption.
            city_slug: Target city and state slug string.
            business_type: Transaction type slug (e.g., 'venda').
            categories: Property categories to iterate over.
            price_ranges: Price range tuples to partition search queries.
            max_pages: Maximum pages to request per partition.
            known_ids: Existing listing IDs in the database for early stopping.
            known_urls: Existing normalised listing URLs in the database.
            *args: Additional positional arguments for ``scrapy.Spider``.
            **kwargs: Additional keyword arguments for ``scrapy.Spider``.
        """
        super().__init__(*args, **kwargs)
        self.store = store
        self.city_slug = city_slug
        self.business_type = business_type
        self.categories = (
            categories if categories is not None else list(PROPERTY_CATEGORIES)
        )
        self.price_ranges = (
            price_ranges if price_ranges is not None else list(PRICE_RANGES)
        )
        self.max_pages = max_pages
        self.known_ids = known_ids or set()
        self.known_urls = known_urls or set()
        self.blocked_events: list[dict[str, Any]] = []

    def start_requests(self) -> Iterable[scrapy.Request]:
        """Generate initial partition requests starting at each partition's resume page."""
        for cat in self.categories:
            search_path = f"{self.business_type}/{cat}/{self.city_slug}"
            for price_min, price_max in self.price_ranges:
                partition_key = make_partition_key(search_path, price_min, price_max)
                if self.store.is_partition_completed(partition_key):
                    continue
                start_page = self.store.get_resume_page(partition_key)
                if start_page > self.max_pages:
                    continue
                url = build_search_url(search_path, start_page, price_min, price_max)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_search_page,
                    meta={
                        "search_path": search_path,
                        "price_min": price_min,
                        "price_max": price_max,
                        "page": start_page,
                        "partition_key": partition_key,
                    },
                    dont_filter=True,
                )

    def parse_search_page(
        self, response: Response
    ) -> Iterable[dict[str, Any] | scrapy.Request]:
        """Parse a search result page, store listings, and schedule the next page if eligible."""
        meta = response.meta
        search_path: str = meta["search_path"]
        price_min: int | None = meta["price_min"]
        price_max: int | None = meta["price_max"]
        page: int = meta["page"]
        partition_key: str = meta["partition_key"]
        label = search_path.split("/")[-1]

        if response.status in (403, 429):
            diagnostics = inspect_html_structure(response.text)
            block_info = {
                "url": response.url,
                "status": response.status,
                "partition_key": partition_key,
                "page": page,
                "is_waf_challenge": diagnostics["is_waf_challenge"],
            }
            self.blocked_events.append(block_info)
            logger.warning(
                "[%s] [Scrapy Transport Block] HTTP %d on page %d (%s). Stopping partition without evasion.",
                label,
                response.status,
                page,
                response.url,
            )
            return

        if response.status in (404, 410) or response.status != 200:
            self.store.record_progress(partition_key, page, completed=True)
            self.store.flush_sync()
            return

        listings = extract_listings_from_html(response.text)
        if not listings:
            self.store.record_progress(partition_key, page, completed=True)
            self.store.flush_sync()
            return

        if self.known_ids or self.known_urls:
            page_ids = {str(item.get("id")) for item in listings if item.get("id")}
            page_urls = {
                norm
                for item in listings
                if item.get("url") and (norm := normalize_url(str(item.get("url"))))
            }
            new_ids = page_ids - self.known_ids
            new_urls = page_urls - self.known_urls
            all_ids_known = bool(self.known_ids) and not new_ids
            all_urls_known = bool(self.known_urls) and bool(page_urls) and not new_urls
            if (all_ids_known or all_urls_known) and page > 1:
                logger.info(
                    "[%s] Page %d: all listings already in DB — stopping partition.",
                    label,
                    page,
                )
                self.store.record_progress(partition_key, page, completed=True)
                self.store.flush_sync()
                return

        self.store.add_many(listings)
        reached_end = page >= self.max_pages
        self.store.record_progress(partition_key, page, completed=reached_end)
        if self.store.buffer_full or reached_end:
            self.store.flush_sync()

        yield from listings

        if not reached_end:
            next_page = page + 1
            next_url = build_search_url(search_path, next_page, price_min, price_max)
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_search_page,
                meta={
                    "search_path": search_path,
                    "price_min": price_min,
                    "price_max": price_max,
                    "page": next_page,
                    "partition_key": partition_key,
                },
                dont_filter=True,
            )


def run_scrapy_extraction(
    city_slug: str = DEFAULT_CITY_SLUG,
    output_filename: str = DEFAULT_OUTPUT_FILENAME,
    max_pages: int = MAX_PAGES_PER_PARTITION,
    known_ids: set[str] | None = None,
    known_urls: set[str] | None = None,
) -> Path:
    """Run the ZapListingSpider using Scrapy's CrawlerProcess and flush results to CSV.

    Args:
        city_slug: Target city and state slug string.
        output_filename: Destination CSV filename under ``data/raw``.
        max_pages: Maximum pages per partition.
        known_ids: Set of existing listing IDs in DB.
        known_urls: Set of existing normalised listing URLs in DB.

    Returns:
        Path to the output CSV file.
    """
    from scrapy.crawler import CrawlerProcess

    output_path = Path("data/raw") / output_filename
    store = CheckpointStore(output_path=output_path, buffer_size=CHECKPOINT_BUFFER_SIZE)

    process = CrawlerProcess(settings=ZapListingSpider.custom_settings)
    process.crawl(
        ZapListingSpider,
        store=store,
        city_slug=city_slug,
        max_pages=max_pages,
        known_ids=known_ids,
        known_urls=known_urls,
    )
    process.start()
    store.flush_sync()
    return output_path
