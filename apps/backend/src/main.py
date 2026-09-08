"""Aplicação principal FastAPI para o serviço de backend e inferência de Machine Learning."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import hf_hub_download
from logging_settings import setup_logger

from .config import settings
from .routers import health_router, prediction_router

logger = setup_logger(__name__)


def load_model_from_hub() -> object:
    """Baixa o modelo do Hugging Face Hub (com cache em disco) e carrega em memória."""
    if not settings.repo_id:
        logger.warning(
            "REPO_ID não foi configurado nas variáveis de ambiente. "
            "A API iniciará sem carregar o modelo de ML até que a variável seja definida."
        )
        return None

    logger.info(
        f"Iniciando verificação/download do modelo do Hugging Face Hub... "
        f"(Repo: '{settings.repo_id}', Arquivo: '{settings.model_filename}')"
    )

    token = settings.hf_token if settings.hf_token else None
    cache_dir = str(settings.hf_cache_dir) if settings.hf_cache_dir else None

    # hf_hub_download faz cache local automaticamente baseado na ETag/hash do commit
    model_path = hf_hub_download(
        repo_id=settings.repo_id,
        filename=settings.model_filename,
        token=token,
        cache_dir=cache_dir,
    )

    logger.info(f"Artefato do modelo localizado em: {model_path}. Carregando em memória...")
    model = joblib.load(model_path)
    logger.info("Modelo de Machine Learning carregado na memória com sucesso!")
    return model


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerenciador de ciclo de vida da aplicação FastAPI.

    - No startup: Baixa/reutiliza em cache o modelo do Hugging Face e carrega em app.state.model.
    - No shutdown: Libera referências para a coleta de lixo.
    """
    logger.info("Iniciando backend da API de Imóveis...")

    try:
        app.state.model = load_model_from_hub()
    except Exception as exc:
        logger.error(
            f"Erro ao carregar o modelo do Hugging Face Hub na inicialização: {exc}",
            exc_info=True,
        )
        app.state.model = None

    yield

    logger.info("Encerrando a API e desalocando modelo da memória...")
    app.state.model = None


app = FastAPI(
    title="Meu Apê - API de Inferência",
    description="API FastAPI de alta performance para inferência de preços de imóveis com modelo treinado XGBoost.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configuração de CORS para permitir requisições do Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Roteadores
app.include_router(health_router)
app.include_router(prediction_router)
