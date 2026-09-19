from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.engine import engine


def _build_session() -> async_sessionmaker[AsyncSession]:
    """Constrói um gerador de sessão assíncrono.

    Returns:
        async_sessionmaker[AsyncSession]: Gerador de sessão assíncrono.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


AsyncSessionLocal: async_sessionmaker[AsyncSession] = _build_session()
