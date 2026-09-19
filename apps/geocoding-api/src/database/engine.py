from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.config import settings


def _build_engine() -> AsyncEngine:
    """Constrói uma engine assíncrona para o banco de dados com um pool de conexão otimizado.

    Returns:
        AsyncEngine: Engine assíncrona configurada.
    """
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
    )


engine: AsyncEngine = _build_engine()
