import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings, setup_logging
from .database.base import Base
from .database.engine import engine
from .rate_limiter import limiter
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

    # Verify/create DB tables (trata indisponibilidade graciosa durante boot em ambiente local/testes)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tabelas do banco de dados verificadas/criadas com sucesso.")
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao banco de dados na inicialização: {e}")

    yield

    logger.info("Encerrando a API de Geocodificação e liberando recursos...")
    await client.aclose()
    await engine.dispose()


app = FastAPI(
    title="API de Geocodificação em Cache",
    description="API FastAPI com cache PostgreSQL, servidor Nominatim, autenticação M2M via API Key e Rate Limiting.",
    version="1.1.0",
    lifespan=lifespan,
)

# Configura o SlowAPI Limiter globalmente
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health_router)
app.include_router(geocoding_router)