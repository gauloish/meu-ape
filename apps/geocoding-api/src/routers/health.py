from fastapi import APIRouter
from src.schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get(
    "/health", 
    response_model=HealthResponse, 
    summary="Verifica se a API está online"
)
async def health_check() -> HealthResponse:
    """Check API health

    Returns:
        HealthResponse: Health response
    """
    return HealthResponse(
        status="online", 
        message="API de Geocodificação rodando!"
    )