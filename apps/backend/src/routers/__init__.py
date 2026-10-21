"""Módulo de roteadores da aplicação Backend."""

from src.routers.health import router as health_router
from src.routers.prediction import router as prediction_router

__all__ = [
    "health_router",
    "prediction_router",
]
