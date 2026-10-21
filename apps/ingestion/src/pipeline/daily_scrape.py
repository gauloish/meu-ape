"""Daily pipeline script orchestrating scraper execution, deduplication, and DB sync.

Steps:
1. Pre-load existing listing IDs from database for fast early termination on known pages.
2. Run asynchronous Zap Imóveis scraper.
3. Deduplicate raw output CSV using physical property signatures.
4. Synchronize new unique listings to PostgreSQL / Vercel database via SQLAlchemy ORM.
"""

import argparse
import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Set

import pandas as pd

from src.data.deduplicator import deduplicate_dataset
from src.database import Base, Session, engine, ListingRepository
from src.scraping.zap_scraper_async import scrape_full_async

logger = logging.getLogger(__name__)


def run_daily_pipeline(
    city_slug: str = "go+goiania",
    concurrency: int = 1,
    max_pages: int = 10,
    dry_run: bool = False,
) -> None:
    """Execute daily incremental scraping, physical deduplication, and database upload.

    Args:
        city_slug: Target city slug string.
        concurrency: Async scraping concurrency limit.
        max_pages: Page limit per partition for daily runs.
        dry_run: If True, skip database persistence step.
    """
    output_filename = f"zap_daily_{date.today().strftime('%Y%m%d')}.csv"

    Base.metadata.create_all(engine)
    known_ids: Set[str] = set()
    try:
        with Session() as session:
            repo = ListingRepository(session)
            known_ids = repo.get_all_ids()
        logger.info("Loaded %d existing listing IDs from database for early termination.", len(known_ids))
    except Exception as exc:
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

    if not raw_path.exists() or raw_path.stat().st_size == 0:
        logger.warning("No new listings scraped. Exiting pipeline.")
        return

    logger.info("=== STEP 2: Physical Deduplication ===")
    dedup_filename = f"zap_daily_{date.today().strftime('%Y%m%d')}_dedup.csv"
    dedup_path = Path("data/processed") / dedup_filename
    deduplicate_dataset(input_file=raw_path, output_file=dedup_path)

    if not dedup_path.exists():
        logger.error("Deduplicated file not found. Exiting.")
        return

    df = pd.read_csv(dedup_path, low_memory=False)
    clean_df = df.where(pd.notnull(df), None)
    records = clean_df.to_dict(orient="records")
    logger.info("Loaded %d deduplicated listing records for database sync.", len(records))

    if dry_run:
        logger.info("[DRY RUN] Skipping database upload.")
        return

    logger.info("=== STEP 3: Database Persistence & Deduplication ===")
    with Session() as session:
        repo = ListingRepository(session)
        inserted_count = repo.add_many(records)

    logger.info(
        "Daily pipeline finished successfully! New listings added to Vercel Postgres: %d / %d",
        inserted_count,
        len(records),
    )


def main() -> None:
    """CLI entry point for daily scrape pipeline."""
    parser = argparse.ArgumentParser(description="Daily ZAP Imóveis scrape and sync pipeline.")
    parser.add_argument("--city", default="go+goiania", help="City slug")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrency limit")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages per partition")
    parser.add_argument("--dry-run", action="store_true", help="Skip database write")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run_daily_pipeline(
        city_slug=args.city,
        concurrency=args.concurrency,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
