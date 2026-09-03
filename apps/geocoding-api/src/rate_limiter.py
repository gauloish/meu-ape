import secrets
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def get_remote_address_or_api_key(request: Request) -> str:
    """Retorna o identificador para o Rate Limiting.

    Prioriza a X-API-Key fornecida no cabeçalho. Se ausente, utiliza o IP do cliente.

    Args:
        request (Request): Requisição HTTP.

    Returns:
        str: Identificador único da origem.
    """
    api_key = request.headers.get("X-API-Key")

    if api_key:
        return f"key:{api_key}"
        
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_remote_address_or_api_key)


def get_rate_limit_default(key: str = "") -> str:
    """Retorna o limite de requisições unitárias dinamicamente com base no identificador/chave do cliente."""
    if key.startswith("key:"):
        api_key = key.split("key:", 1)[1]
        if secrets.compare_digest(api_key, settings.geo_api_key_ml):
            return settings.rate_limit_ml_default
    return settings.rate_limit_app_default


def get_rate_limit_batch(key: str = "") -> str:
    """Retorna o limite de requisições em lote dinamicamente com base no identificador/chave do cliente."""
    if key.startswith("key:"):
        api_key = key.split("key:", 1)[1]
        if secrets.compare_digest(api_key, settings.geo_api_key_ml):
            return settings.rate_limit_ml_batch
    return settings.rate_limit_app_batch
