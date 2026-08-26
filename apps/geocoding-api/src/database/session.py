from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import engine


def _build_session() -> async_sessionmaker[AsyncSession]:
    """Build asynchronous session maker.

    Returns:
        async_sessionmaker[AsyncSession]: Asynchronous session maker.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


AsyncSessionLocal: async_sessionmaker[AsyncSession] = _build_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session to be used in API endpoints."""
    async with AsyncSessionLocal() as session:
        yield session