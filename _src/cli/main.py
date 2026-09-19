"""Command-line interface module for the meu-ape data pipeline.

Provides subcommands for synchronous extraction, asynchronous extraction, dataset
deduplication, and catalog coverage validation.
"""

import argparse
import asyncio
import logging
import sys


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


def cmd_deduplicate(args: argparse.Namespace) -> None:
    """Execute physical asset deduplication."""
    from pathlib import Path
    from src.data.deduplicator import deduplicate_dataset
    output = deduplicate_dataset(
        input_file=Path(args.input),
        output_file=Path(args.output),
    )
    print(f"Deduplication completed. Output saved to: {output.resolve()}")


def cmd_daily_scrape(args: argparse.Namespace) -> None:
    """Execute end-to-end daily scrape, deduplication, and DB sync."""
    from src.pipeline.daily_scrape import run_daily_pipeline
    run_daily_pipeline(
        city_slug=args.city,
        concurrency=args.concurrency,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )



def cmd_load_csv(args: argparse.Namespace) -> None:
    """Execute bulk CSV dataset load into database."""
    from pathlib import Path
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
        description="Real estate data extraction and processing pipeline for Zap Imóveis.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logging"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p_scrape = sub.add_parser("scrape", help="Execute synchronous multi-threaded extraction")
    p_scrape.add_argument("--city", default="go+goiania", metavar="SLUG", help="City and state slug")
    p_scrape.add_argument("--output", default="zap_dataset.csv", metavar="FILENAME", help="Output filename")
    p_scrape.add_argument("--workers", type=int, default=1, metavar="N", help="Worker thread count")
    p_scrape.add_argument("--delay-min", type=float, default=3.0, dest="delay_min", help="Minimum request delay")
    p_scrape.add_argument("--delay-max", type=float, default=6.0, dest="delay_max", help="Maximum request delay")
    p_scrape.set_defaults(func=cmd_scrape)

    p_async = sub.add_parser("scrape-async", help="Execute high-speed asynchronous extraction")
    p_async.add_argument("--city", default="go+goiania", metavar="SLUG", help="City and state slug")
    p_async.add_argument("--output", default="zap_dataset.csv", metavar="FILENAME", help="Output filename")
    p_async.add_argument("--concurrency", type=int, default=1, metavar="N", help="Concurrency semaphore limit")
    p_async.set_defaults(func=cmd_scrape_async)

    p_daily = sub.add_parser("daily-scrape", help="Execute daily scrape, deduplication, and database upload")
    p_daily.add_argument("--city", default="go+goiania", metavar="SLUG", help="City and state slug")
    p_daily.add_argument("--concurrency", type=int, default=1, metavar="N", help="Concurrency limit")
    p_daily.add_argument("--max-pages", type=int, default=10, metavar="N", help="Max pages per partition")
    p_daily.add_argument("--dry-run", action="store_true", help="Skip writing to database")
    p_daily.set_defaults(func=cmd_daily_scrape)


    p_load = sub.add_parser("load-csv", help="Bulk load existing CSV dataset into database")
    p_load.add_argument("--input", default="data/processed/zap_dataset_deduplicated.csv", metavar="PATH", help="Input CSV path")
    p_load.add_argument("--chunk-size", type=int, default=2000, metavar="N", help="Batch size per transaction")
    p_load.set_defaults(func=cmd_load_csv)

    p_dedup = sub.add_parser("deduplicate", help="Remove physical duplicate listings from raw dataset")


    p_dedup.add_argument(
        "--input", default="data/raw/zap_dataset.csv", metavar="PATH", help="Raw input CSV path"
    )
    p_dedup.add_argument(
        "--output", default="data/processed/zap_dataset_deduplicated.csv", metavar="PATH", help="Processed output CSV path"
    )
    p_dedup.set_defaults(func=cmd_deduplicate)

    p_val = sub.add_parser("validate", help="Validate local dataset coverage against official portal totals")
    p_val.set_defaults(func=cmd_validate)

    return parser


def main(argv=None) -> None:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
