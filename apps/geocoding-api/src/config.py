import logging
import sys


def get_format_str(color: str, reset: str) -> str:
    """Get format string with color and reset color.

    Args:
        color (str): Color code.
        reset (str): Reset code.

    Returns:
        str: Formatted string to logger.
    """
    return f"[%(asctime)s][%(name)s] {color}%(levelname)s{reset}: %(message)s"


class ColorFormatter(logging.Formatter):
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT_STR = f"[%(asctime)s][%(name)s] %(levelname)s: %(message)s"

    FORMATS = {
        logging.DEBUG: get_format_str(GREY, RESET),
        logging.INFO: get_format_str(BLUE, RESET),
        logging.WARNING: get_format_str(YELLOW, RESET),
        logging.ERROR: get_format_str(RED, RESET),
        logging.CRITICAL: get_format_str(BOLD_RED, RESET),
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT_STR)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging():
    """Configura o logger global da aplicação."""
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    console_handler.setFormatter(ColorFormatter())
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler]
    )