from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..config import settings
from .config import DATABASE_URL


def _build_engine() -> AsyncEngine:
    """Build async engine to database with optimized connection pool.

    Returns:
        AsyncEngine: Configured async database engine.
    """
    return create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
    )


engine: AsyncEngine = _build_engine()