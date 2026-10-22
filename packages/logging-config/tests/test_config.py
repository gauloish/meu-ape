"""Testes unitários para o pacote logging-config."""

import io
from unittest.mock import patch

from logging_config import config_logger
from loguru import logger


def test_config_logger_levels_and_colors():
    """Valida a configuração de níveis e cores do Loguru."""
    config_logger()

    assert logger.level("DEBUG").color == "<cyan>"
    assert logger.level("INFO").color == "<green>"
    assert logger.level("WARNING").color == "<magenta>"
    assert logger.level("ERROR").color == "<red>"
    assert logger.level("CRITICAL").color == "<red><bold>"


def test_config_logger_output_formatting():
    """Valida a formatação da mensagem de log no stdout."""
    # Redireciona stdout temporariamente para capturar o log formatado
    stream = io.StringIO()
    logger.remove()

    config_logger()
    handler_id = logger.add(
        sink=stream, format="[ {name}:{function} ] [ {level} ] {message}"
    )

    logger.info("Mensagem de teste de log")
    output = stream.getvalue()

    assert "Mensagem de teste de log" in output
    assert "INFO" in output
    logger.remove(handler_id)


def test_config_logger_resets_handlers():
    """Garante que config_logger remove handlers anteriores para evitar duplicações."""
    with patch.object(logger, "remove") as mock_remove:
        config_logger()
        mock_remove.assert_called_once()


def test_config_logger_idempotence():
    """Garante que chamadas sucessivas de config_logger não geram múltiplos sinks duplicados."""
    config_logger()
    config_logger()

    stream = io.StringIO()
    handler_id = logger.add(sink=stream, format="{message}")
    logger.info("Log único")
    logger.remove(handler_id)

    assert stream.getvalue().count("Log único") == 1
