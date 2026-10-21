"""Pipeline module orchestrating multi-stage scraping, deduplication, and DB sync."""

from src.pipeline.daily_scrape import run_daily_pipeline

__all__ = ["run_daily_pipeline"]
