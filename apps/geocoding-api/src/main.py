import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from database.engine import engine
from database.base import Base

from src.routers import geocoding_router, health_router


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando a API e verificando o banco de dados...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tabelas verificadas/criadas com sucesso.")
    
    yield
    
    logger.info("Encerrando a API...")
    await engine.dispose()

app = FastAPI(
    title="API de Geocodificação em Cache",
    description="API com FastAPI e PostgreSQL para geocodificação com Nominatim",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(health_router)
app.include_router(geocoding_router)