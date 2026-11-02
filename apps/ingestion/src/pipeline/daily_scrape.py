"""Daily pipeline script orchestrating scraper execution, fallback, deduplication, and DB sync.

Steps:
1. Pre-load existing listing IDs from database for fast early termination on known pages.
2. Run asynchronous Zap Imóveis scraper (or switch to local fallback when blocked).
3. Deduplicate raw output CSV by ID, canonical URL, and physical property signature.
4. Synchronize unique listings and price history to PostgreSQL via SQLAlchemy ORM.
"""

import argparse
import asyncio
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from src.data.deduplicator import deduplicate_dataset
from src.data.price_index import (
    apply_fipezap_to_dataframe,
    compute_cumulative_factor,
    resolve_fallback_dataset,
)
from src.database import Base, ListingRepository, Session, engine
from src.scraping.zap_scraper_async import scrape_full_async

logger = logging.getLogger(__name__)


def run_fipezap_update(
    months: list[str] | None = None,
    custom_rate_pct: float | None = None,
    dry_run: bool = False,
) -> int:
    """Apply the public FipeZAP Goiânia index to stored listings and record price history.

    Args:
        months: Optional list of ``YYYY-MM`` reference months.
        custom_rate_pct: Optional explicit percentage variation (e.g. ``0.83`` for +0.83%).
        dry_run: If True, compute factor without modifying database records.

    Returns:
        Number of updated listings in the database.
    """
    Base.metadata.create_all(engine)
    custom_list = [custom_rate_pct] if custom_rate_pct is not None else None
    factor = compute_cumulative_factor(months=months, custom_rates_pct=custom_list)
    logger.info("Computed FipeZAP Goiânia adjustment factor: %.6f", factor)

    if dry_run:
        logger.info("[DRY RUN] Skipping FipeZAP database update.")
        return 0

    with Session() as session:
        repo = ListingRepository(session)
        updated = repo.apply_price_index(factor=factor, source="fipezap_index")

    logger.info(
        "FipeZAP price adjustment complete: %d listings updated and logged in price history.",
        updated,
    )
    return updated


def run_daily_pipeline(
    city_slug: str = "go+goiania",
    concurrency: int = 1,
    max_pages: int = 10,
    dry_run: bool = False,
    fallback_csv: Path | None = None,
    apply_fipezap: bool = False,
) -> None:
    """Execute daily incremental scraping, fallback handling, deduplication, and DB sync.

    When live scraping returns no records (e.g., due to edge WAF HTTP 403/429 blocks),
    automatically checks for a local Goiânia dataset so the downstream pipeline
    continues operating without interruption.

    Args:
        city_slug: Target city slug string.
        concurrency: Async scraping concurrency limit.
        max_pages: Page limit per partition for daily runs.
        dry_run: If True, skip database persistence step.
        fallback_csv: Optional explicit CSV dataset to use if live scraping is blocked.
        apply_fipezap: If True, apply FipeZAP index adjustment to fallback records.
    """
    output_filename = f"zap_daily_{date.today().strftime('%Y%m%d')}.csv"

    Base.metadata.create_all(engine)
    known_ids: set[str] = set()
    try:
        with Session() as session:
            repo = ListingRepository(session)
            known_ids = repo.get_all_ids()
        logger.info(
            "Loaded %d existing listing IDs from database for early termination.",
            len(known_ids),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not pre-fetch existing IDs from database: %s", exc)

    logger.info("=== STEP 1: Running Zap Imóveis Async Scraper ===")
    raw_path = asyncio.run(
        scrape_full_async(
            city_slug=city_slug,
            output_filename=output_filename,
            concurrency=concurrency,
            known_ids=known_ids,
            max_pages=max_pages,
        )
    )

    source_label = "zap_scrape"
    if not raw_path.exists() or raw_path.stat().st_size == 0:
        fallback_path = resolve_fallback_dataset(fallback_csv)
        if fallback_path is None:
            logger.warning("No new listings scraped. Exiting pipeline.")
            return
        logger.warning(
            "Live scraping blocked or returned 0 listings. Falling back to local dataset: %s",
            fallback_path,
        )
        raw_path = fallback_path
        source_label = "local_fallback"

    logger.info("=== STEP 2: Physical, URL & ID Deduplication ===")
    dedup_filename = f"zap_daily_{date.today().strftime('%Y%m%d')}_dedup.csv"
    dedup_path = Path("data/processed") / dedup_filename
    deduplicate_dataset(input_file=raw_path, output_file=dedup_path)

    if not dedup_path.exists():
        logger.error("Deduplicated file not found. Exiting.")
        return

    df = pd.read_csv(dedup_path, low_memory=False)
    if apply_fipezap:
        factor = compute_cumulative_factor()
        logger.info(
            "Applying FipeZAP Goiânia adjustment factor (%.6f) to %d records.",
            factor,
            len(df),
        )
        df = apply_fipezap_to_dataframe(df, factor)
        source_label = "fipezap_index"

    clean_df = df.where(pd.notnull(df), None)
    records = clean_df.to_dict(orient="records")
    logger.info(
        "Loaded %d deduplicated listing records for database sync.", len(records)
    )

    if dry_run:
        logger.info("[DRY RUN] Skipping database upload.")
        return

    logger.info("=== STEP 3: Database Persistence, Deduplication & Price History ===")
    with Session() as session:
        repo = ListingRepository(session)
        inserted_count = repo.add_many(records, source=source_label)

    logger.info(
        "Daily pipeline finished successfully! New listings added to PostgreSQL: %d / %d",
        inserted_count,
        len(records),
    )


def main() -> None:
    """CLI entry point for daily scrape pipeline."""
    parser = argparse.ArgumentParser(
        description="Daily ZAP Imóveis scrape and sync pipeline."
    )
    parser.add_argument("--city", default="go+goiania", help="City slug")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrency limit")
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Max pages per partition"
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip database write")
    parser.add_argument(
        "--fallback-csv",
        default=None,
        help="Optional local CSV path when live scraping is blocked",
    )
    parser.add_argument(
        "--apply-fipezap",
        action="store_true",
        help="Apply FipeZAP Goiânia price adjustment factor",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    run_daily_pipeline(
        city_slug=args.city,
        concurrency=args.concurrency,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
        fallback_csv=Path(args.fallback_csv) if args.fallback_csv else None,
        apply_fipezap=args.apply_fipezap,
    )


if __name__ == "__main__":
    main()
