import logging
import sys
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = Field(default="user", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="cache_db", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="geocoding_database", validation_alias="POSTGRES_DB")

    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=1800, validation_alias="DB_POOL_RECYCLE")

    nominatim_url: str = Field(default="http://nominatim_server:8080", validation_alias="NOMINATIM_URL")
    user_agent: str = Field(default="GeocodingAPI/1.0", validation_alias="USER_AGENT")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
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