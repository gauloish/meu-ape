"""Roteador para verificação de saúde e prontidão da aplicação (Health Check)."""

from fastapi import APIRouter, Request
from ..schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificação de integridade e prontidão da API",
)
def health_check(request: Request) -> HealthResponse:
    """Retorna o status de execução da API e a disponibilidade do modelo de ML."""
    model_loaded = getattr(request.app.state, "model", None) is not None
    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
    )
