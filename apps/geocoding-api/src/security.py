import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Valida a API Key fornecida no cabeçalho X-API-Key usando comparação segura.

    Args:
        api_key (str | None): Chave recebida no cabeçalho HTTP.

    Returns:
        str: A chave validada.

    Raises:
        HTTPException: 401 Unauthorized se a chave for nula ou inválida.
    """
    if not api_key or not secrets.compare_digest(api_key, settings.geo_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API (X-API-Key) inválida ou ausente.",
        )
    return api_key
