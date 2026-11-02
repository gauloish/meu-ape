"""Command-line interface module for the meu-ape data pipeline.

Provides subcommands for synchronous extraction, asynchronous extraction, Scrapy
extraction, dataset deduplication, FipeZAP price index adjustment, and catalog
coverage validation.
"""

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any


def _setup_logging(verbose: bool) -> None:
    """Configure logging format and verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def cmd_scrape(args: argparse.Namespace) -> None:
    """Execute synchronous multi-threaded scraper."""
    from src.scraping.zap_scraper_sync import scrape_full

    output = scrape_full(
        city_slug=args.city,
        output_filename=args.output,
        max_workers=args.workers,
        delay_range=(args.delay_min, args.delay_max),
    )
    print(f"Extraction completed. Dataset saved to: {output.resolve()}")


def cmd_scrape_async(args: argparse.Namespace) -> None:
    """Execute asynchronous scraper."""
    from src.scraping.zap_scraper_async import scrape_full_async

    output = asyncio.run(
        scrape_full_async(
            city_slug=args.city,
            output_filename=args.output,
            concurrency=args.concurrency,
        )
    )
    print(f"Async extraction completed. Dataset saved to: {output.resolve()}")


def cmd_scrape_scrapy(args: argparse.Namespace) -> None:
    """Execute Scrapy spider extraction."""
    from src.scraping.scrapy_spider import run_scrapy_extraction

    output = run_scrapy_extraction(
        city_slug=args.city,
        output_filename=args.output,
        max_pages=args.max_pages,
    )
    print(f"Scrapy extraction completed. Dataset saved to: {output.resolve()}")


def cmd_deduplicate(args: argparse.Namespace) -> None:
    """Execute physical, URL, and ID asset deduplication."""
    from src.data.deduplicator import deduplicate_dataset

    output = deduplicate_dataset(
        input_file=Path(args.input),
        output_file=Path(args.output),
    )
    print(f"Deduplication completed. Output saved to: {output.resolve()}")


def cmd_daily_scrape(args: argparse.Namespace) -> None:
    """Execute end-to-end daily scrape, deduplication, fallback, and DB sync."""
    from src.pipeline.daily_scrape import run_daily_pipeline

    kwargs: dict[str, Any] = {
        "city_slug": args.city,
        "concurrency": args.concurrency,
        "max_pages": args.max_pages,
        "dry_run": args.dry_run,
    }
    if getattr(args, "fallback_csv", None) is not None:
        kwargs["fallback_csv"] = Path(args.fallback_csv)
    if getattr(args, "apply_fipezap", False):
        kwargs["apply_fipezap"] = True

    run_daily_pipeline(**kwargs)


def cmd_apply_index(args: argparse.Namespace) -> None:
    """Apply FipeZAP Goiânia index adjustment to database listings and record price history."""
    from src.pipeline.daily_scrape import run_fipezap_update

    months = (
        [m.strip() for m in args.months.split(",") if m.strip()]
        if args.months
        else None
    )
    updated = run_fipezap_update(
        months=months,
        custom_rate_pct=args.rate,
        dry_run=args.dry_run,
    )
    print(f"FipeZAP price adjustment finished. Listings updated: {updated}")


def cmd_load_csv(args: argparse.Namespace) -> None:
    """Execute bulk CSV dataset load into database."""
    from src.pipeline.load_csv import load_csv_to_db

    load_csv_to_db(csv_file=Path(args.input), chunk_size=args.chunk_size)


def cmd_validate(_args: argparse.Namespace) -> None:
    """Execute coverage validation check."""
    from src.data.validator import validate_coverage

    validate_coverage()


def build_parser() -> argparse.ArgumentParser:
    """Construct and configure command-line argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="meu-ape",
        description="Real estate data extraction and processing pipeline for Goiânia.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logging"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p_scrape = sub.add_parser(
        "scrape", help="Execute synchronous multi-threaded extraction"
    )
    p_scrape.add_argument(
        "--city", default="go+goiania", metavar="SLUG", help="City and state slug"
    )
    p_scrape.add_argument(
        "--output",
        default="zap_dataset.csv",
        metavar="FILENAME",
        help="Output filename",
    )
    p_scrape.add_argument(
        "--workers", type=int, default=1, metavar="N", help="Worker thread count"
    )
    p_scrape.add_argument(
        "--delay-min",
        type=float,
        default=3.0,
        dest="delay_min",
        help="Minimum request delay",
    )
    p_scrape.add_argument(
        "--delay-max",
        type=float,
        default=6.0,
        dest="delay_max",
        help="Maximum request delay",
    )
    p_scrape.set_defaults(func=cmd_scrape)

    p_async = sub.add_parser("scrape-async", help="Execute asynchronous extraction")
    p_async.add_argument(
        "--city", default="go+goiania", metavar="SLUG", help="City and state slug"
    )
    p_async.add_argument(
        "--output",
        default="zap_dataset.csv",
        metavar="FILENAME",
        help="Output filename",
    )
    p_async.add_argument(
        "--concurrency",
        type=int,
        default=1,
        metavar="N",
        help="Concurrency semaphore limit",
    )
    p_async.set_defaults(func=cmd_scrape_async)

    p_scrapy = sub.add_parser(
        "scrape-scrapy", help="Execute Scrapy spider extraction obeying robots.txt"
    )
    p_scrapy.add_argument(
        "--city", default="go+goiania", metavar="SLUG", help="City and state slug"
    )
    p_scrapy.add_argument(
        "--output",
        default="zap_dataset.csv",
        metavar="FILENAME",
        help="Output filename",
    )
    p_scrapy.add_argument(
        "--max-pages",
        type=int,
        default=10,
        metavar="N",
        help="Max pages per partition",
    )
    p_scrapy.set_defaults(func=cmd_scrape_scrapy)

    p_daily = sub.add_parser(
        "daily-scrape", help="Execute daily scrape, deduplication, and database upload"
    )
    p_daily.add_argument(
        "--city", default="go+goiania", metavar="SLUG", help="City and state slug"
    )
    p_daily.add_argument(
        "--concurrency", type=int, default=1, metavar="N", help="Concurrency limit"
    )
    p_daily.add_argument(
        "--max-pages", type=int, default=10, metavar="N", help="Max pages per partition"
    )
    p_daily.add_argument(
        "--dry-run", action="store_true", help="Skip writing to database"
    )
    p_daily.add_argument(
        "--fallback-csv",
        default=None,
        metavar="PATH",
        help="Fallback CSV path when live scraping is blocked",
    )
    p_daily.add_argument(
        "--apply-fipezap",
        action="store_true",
        help="Apply FipeZAP Goiânia price adjustment factor",
    )
    p_daily.set_defaults(func=cmd_daily_scrape)

    p_index = sub.add_parser(
        "apply-index",
        help="Apply public FipeZAP Goiânia price index to stored listings",
    )
    p_index.add_argument(
        "--months",
        default=None,
        metavar="YYYY-MM,...",
        help="Comma-separated reference months from FipeZAP Goiânia series",
    )
    p_index.add_argument(
        "--rate",
        type=float,
        default=None,
        metavar="PCT",
        help="Explicit percentage adjustment (e.g. 0.83 for +0.83%%)",
    )
    p_index.add_argument(
        "--dry-run", action="store_true", help="Compute factor without writing to DB"
    )
    p_index.set_defaults(func=cmd_apply_index)

    p_load = sub.add_parser(
        "load-csv", help="Bulk load existing CSV dataset into database"
    )
    p_load.add_argument(
        "--input",
        default="data/processed/zap_dataset_deduplicated.csv",
        metavar="PATH",
        help="Input CSV path",
    )
    p_load.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        metavar="N",
        help="Batch size per transaction",
    )
    p_load.set_defaults(func=cmd_load_csv)

    p_dedup = sub.add_parser(
        "deduplicate", help="Remove physical, URL, and ID duplicate listings"
    )
    p_dedup.add_argument(
        "--input",
        default="data/raw/zap_dataset.csv",
        metavar="PATH",
        help="Raw input CSV path",
    )
    p_dedup.add_argument(
        "--output",
        default="data/processed/zap_dataset_deduplicated.csv",
        metavar="PATH",
        help="Processed output CSV path",
    )
    p_dedup.set_defaults(func=cmd_dedup_alias)

    p_val = sub.add_parser(
        "validate",
        help="Validate local dataset coverage against official portal totals",
    )
    p_val.set_defaults(func=cmd_validate)

    return parser


def cmd_dedup_alias(args: argparse.Namespace) -> None:
    """Alias wrapper for cmd_deduplicate."""
    cmd_deduplicate(args)


def main(argv=None) -> None:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
