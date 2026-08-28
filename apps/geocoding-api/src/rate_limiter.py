from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


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
