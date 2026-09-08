"""Injeção de dependências compartilhadas do FastAPI."""

from typing import Any
from fastapi import HTTPException, Request, status


def get_model(request: Request) -> Any:
    """Recupera a instância do modelo de Machine Learning carregada no Lifespan.

    Args:
        request (Request): Objeto de requisição HTTP do FastAPI.

    Returns:
        Any: Pipeline / Modelo de Machine Learning deserializado.

    Raises:
        HTTPException: Caso o modelo não tenha sido carregado na memória.
    """
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O modelo de Machine Learning não está carregado ou ainda está sendo inicializado.",
        )
    return model
