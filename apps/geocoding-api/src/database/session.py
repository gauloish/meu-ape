from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .engine import engine


def _build_session() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


AsyncSessionLocal: async_sessionmaker[AsyncSession] = _build_session()