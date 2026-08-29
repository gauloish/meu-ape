"""Módulo de configuração do pacote geocoding-client.

Este módulo utiliza Pydantic Settings para carregar e validar as variáveis de ambiente
da aplicação cliente, tais como a URL base da API e a chave de autenticação M2M.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClientSettings(BaseSettings):
    """Gerencia as configurações de ambiente do cliente de Geocodificação.

    Atributos e variáveis de ambiente suportadas:
        geo_api_url (str): URL base da API interna (Variável: `GEO_API_URL`).
        geo_api_key (str): Chave M2M enviada no cabeçalho X-API-Key (Variável: `GEO_API_KEY`).
        timeout (float): Tempo limite padrão para requisições HTTP em segundos (Variável: `GEO_TIMEOUT`).
        max_retries (int): Número máximo de tentativas do Exponential Backoff (Variável: `GEO_MAX_RETRIES`).
        backoff_factor (float): Fator multiplicador do atraso exponencial (Variável: `GEO_BACKOFF_FACTOR`).
    """

    geo_api_url: str = Field(
        default="http://localhost:8000",
        description="URL base da API interna de Geocodificação (ex: GEO_API_URL)",
    )
    
    geo_api_key: str = Field(
        default="geocoding_secret_key_change_me",
        description="Chave de autenticação M2M enviada via X-API-Key (ex: GEO_API_KEY)",
    )

    timeout: float = Field(
        default=15.0,
        description="Timeout padrão das requisições em segundos",
    )

    max_retries: int = Field(
        default=4,
        description="Número máximo de tentativas no exponential backoff em 429/5xx",
    
    )
    backoff_factor: float = Field(
        default=1.5,
        description="Fator multiplicador do intervalo de backoff exponencial em segundos",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = ClientSettings()
