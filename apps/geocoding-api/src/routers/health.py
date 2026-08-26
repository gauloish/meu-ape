import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.session import get_db
from ..schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verifica se a API e suas dependências estão ativas",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> HealthResponse:
    """Diagnóstico ativo da API, PostgreSQL e Nominatim."""
    db_healthy = False
    nominatim_healthy = False

    # Check Database
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_healthy = True
    except Exception as e:
        logger.error(f"Health check DB error: {e}")

    # Check Nominatim
    try:
        resp = await client.get(
            f"{settings.nominatim_url}/status",
            params={"format": "json"},
            timeout=3.0,
        )
        if resp.status_code == 200:
            nominatim_healthy = True
        else:
            # Fallback check search if status endpoint is not present
            resp_fallback = await client.get(
                f"{settings.nominatim_url}/search",
                params={"q": "Goiânia", "format": "json", "limit": 1},
                timeout=3.0,
            )
            if resp_fallback.status_code == 200:
                nominatim_healthy = True
    except Exception as e:
        logger.error(f"Health check Nominatim error: {e}")

    overall_status = "online" if (db_healthy and nominatim_healthy) else "degraded" if (db_healthy or nominatim_healthy) else "offline"
    msg = "Todos os serviços operacionais." if overall_status == "online" else "Uma ou mais dependências estão indisponíveis."

    health_data = HealthResponse(
        status=overall_status,
        message=msg,
        database=db_healthy,
        nominatim=nominatim_healthy,
    )

    if not db_healthy or not nominatim_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_data.model_dump(),
        )

    return health_data