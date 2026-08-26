import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request

from .config import settings, setup_logging
from .database.base import Base
from .database.engine import engine
from .routers import geocoding_router, health_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Iniciando a API de Geocodificação...")

    # Configure persistent global HTTP client
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=100, keepalive_expiry=30.0)
    timeout = httpx.Timeout(15.0, connect=5.0)
    client = httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        headers={"User-Agent": settings.user_agent},
    )
    app.state.http_client = client

    # Verify/create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas do banco de dados verificadas/criadas com sucesso.")

    yield

    logger.info("Encerrando a API de Geocodificação e liberando recursos...")
    await client.aclose()
    await engine.dispose()


app = FastAPI(
    title="API de Geocodificação em Cache",
    description="API FastAPI com cache PostgreSQL e servidor Nominatim para geocodificação direta e reversa.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_http_client(request: Request) -> httpx.AsyncClient:
    """FastAPI Dependency to get global shared httpx.AsyncClient."""
    return request.app.state.http_client


app.include_router(health_router)
app.include_router(geocoding_router)