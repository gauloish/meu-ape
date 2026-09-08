"""Script de inicialização direta para execução local via python ou uvicorn."""

import uvicorn
from src.config import settings
from src.main import app

__all__ = ["app"]


def run():
    """Inicia o servidor uvicorn com as configurações de ambiente."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    run()
