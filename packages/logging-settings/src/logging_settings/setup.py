
import logging
import sys

from .formatter import ColorFormatter


def setup_logger(
    name: str,
    level: str | None = "INFO",
    use_color: bool = True
) -> logging.Logger:
    """
    Configura o logger para a aplicação.
    
    Args:
        name: Nome do logger.
        level: Nível de log.
        use_color: Se deve usar cores no log.
    
    Returns:
        Logger configurado.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if use_color:
        console_handler.setFormatter(ColorFormatter())

    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        handlers=[console_handler],
        force=True,
    )

    return logging.getLogger(name)