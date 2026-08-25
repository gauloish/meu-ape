from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from .config import DATABASE_URL


def _build_engine() -> AsyncEngine:
    """Build async engine to database.

    Returns:
        AsyncEngine: Async engine to database.
    """
    return create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True
    )


engine: AsyncEngine = _build_engine()