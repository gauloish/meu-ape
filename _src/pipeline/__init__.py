"""Pipeline module orchestrating multi-stage scraping, deduplication, and DB sync."""

from .daily_scrape import run_daily_pipeline

__all__ = ["run_daily_pipeline"]
