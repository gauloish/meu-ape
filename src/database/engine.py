"""SQLAlchemy engine factory supporting both PostgreSQL (Vercel/Neon) and local SQLite.

The engine is resolved in this priority order:
1. ``DATABASE_URL`` environment variable (Postgres connection string for production).
2. Local SQLite file at ``data/cache/geocoding.db`` (development fallback).

The ``DATABASE_URL`` must use the ``postgresql+psycopg://`` scheme to be compatible
with the psycopg v3 driver required by SQLAlchemy 2.x async support.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _build_engine() -> Engine:
    """Build the SQLAlchemy engine from environment or local fallback.

    Returns:
        Configured SQLAlchemy Engine instance.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Vercel/Neon provides a postgres:// URL; SQLAlchemy requires the dialect prefix.
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return create_engine(database_url, pool_pre_ping=True)

    # Local SQLite fallback for development
    db_path = PROJECT_ROOT / "data" / "cache" / "geocoding.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


engine = _build_engine()
