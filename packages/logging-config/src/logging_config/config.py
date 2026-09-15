import sys

from loguru import logger


def config_logger() -> None:
    """Faz a configuração do logger com formatação da mensagem de logging com cores no terminal."""
    logger.remove()

    logger.level(name="DEBUG", color="<cyan>")
    logger.level(name="INFO", color="<green>")
    logger.level(name="WARNING", color="<magenta>")
    logger.level(name="ERROR", color="<red>")
    logger.level(name="CRITICAL", color="<red><bold>")

    format = (
        "[<bold>{name}:{function}</bold>] "
        "[<blue>{time:YYYY-MM-DD HH:mm:ss}</blue>] "
        "[<level>{level}</level>] "
        "{message}"
    )

    logger.add(
        sink=sys.stdout,
        format=format,
    )
