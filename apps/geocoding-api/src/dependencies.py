from collections.abc import AsyncGenerator
import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from .database.session import AsyncSessionLocal


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Injeta o cliente HTTP compartilhado (httpx.AsyncClient) armazenado no estado da aplicação."""
    return request.app.state.http_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Injeta uma sessão assíncrona do banco de dados PostgreSQL."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
