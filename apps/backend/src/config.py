"""Módulo de configurações da aplicação Backend usando Pydantic Settings."""

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da API de Inferência carregadas a partir de variáveis de ambiente."""

    # Hugging Face Hub Configuration
    hf_token: str | None = Field(
        default=None,
        description="Token de autenticação do Hugging Face Hub (obrigatório para repos privados).",
    )
    repo_id: str = Field(
        default="",
        description="ID do repositório de modelos no Hugging Face (ex: 'usuario/meu-ape-model').",
    )
    model_filename: str = Field(
        default="model.joblib",
        description="Nome do arquivo serializado do modelo no Hugging Face Hub.",
    )
    hf_cache_dir: Path | None = Field(
        default=None,
        description="Diretório customizado de cache para downloads do Hugging Face Hub.",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Host de binding do servidor.")
    port: int = Field(default=8001, description="Porta HTTP do servidor.")
    log_level: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR).")

    # CORS Configuration
    cors_origins: str = Field(
        default="*",
        description="Lista de origens permitidas para CORS, separadas por vírgula ou '*' para todas.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna as origens CORS como lista de strings."""
        if not self.cors_origins:
            return ["*"]
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
