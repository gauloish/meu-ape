import logging
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "user"
    postgres_password: str = "password"
    postgres_host: str = "cache_db"
    postgres_port: int = 5432
    postgres_db: str = "geocoding_database"

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    nominatim_url: str = "http://nominatim_server:8080"
    user_agent: str = "GeocodingAPI/1.0"

    log_level: str = "INFO"

    # Security (SecOps) & Rate Limiting por Perfil
    geo_api_key_app: str = Field(default="geocoding_secret_key_change_me", description="Chave para consumo comum (Backend)")
    geo_api_key_ml: str = Field(default="geocoding_ml_secret_key_change_me", description="Chave para pipeline de ML")

    rate_limit_app_default: str = Field(default="60/minute", description="Limite padrão para consumo comum (unitário)")
    rate_limit_app_batch: str = Field(default="10/minute", description="Limite padrão para consumo comum (em lote)")
    rate_limit_ml_default: str = Field(default="600/minute", description="Limite padrão para pipeline de ML (unitário)")
    rate_limit_ml_batch: str = Field(default="120/minute", description="Limite padrão para pipeline de ML (em lote)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()


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

    FORMAT_STR = "[%(asctime)s][%(name)s] %(levelname)s: %(message)s"

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


def setup_logging() -> None:
    """Setup global logger application."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColorFormatter())

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler],
        force=True,
    )