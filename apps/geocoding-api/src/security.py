import secrets
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> str:
    """Valida a API Key fornecida no cabeçalho X-API-Key e identifica o perfil do cliente (tier).

    Args:
        request (Request): Objeto da requisição HTTP FastAPI.
        api_key (str | None): Chave recebida no cabeçalho HTTP.

    Returns:
        str: A chave validada.

    Raises:
        HTTPException: 401 Unauthorized se a chave for nula ou inválida.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API (X-API-Key) inválida ou ausente.",
        )

    if secrets.compare_digest(api_key, settings.geo_api_key_ml):
        request.state.client_tier = "ml"
    elif secrets.compare_digest(api_key, settings.geo_api_key_app):
        request.state.client_tier = "app"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API (X-API-Key) inválida ou ausente.",
        )

    return api_key
