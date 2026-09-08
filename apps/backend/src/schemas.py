"""Schemas de validação e serialização de dados (Pydantic) para a API de inferência."""

from pydantic import BaseModel, Field
from typing import Literal


MIN_LATITUDE: float = -16.85
MAX_LATITUDE: float = -16.55

MIN_LONGITUDE: float = -49.45
MAX_LONGITUDE: float = -49.15


class InferenceRequest(BaseModel):
    """Schema de entrada para inferência de preço de imóvel."""

    # Variáveis Textuais
    tipo_imovel: Literal["apartamento","casa", "cobertura", "sobrado", "flat", "studio", "outro"] = Field(description="Tipo do imóvel (casa, apartamento, etc)")

    # Variáveis Numéricas
    condominio: int = Field(ge=0, le=5000, description="Valor do condomínio em R$")
    area_m2: int = Field(ge=20, le=1000, description="Área útil do imóvel em metros quadrados (m²)")
    quartos: int = Field(ge=0, le=8, description="Quantidade de quartos no imóvel")
    banheiros: int = Field(ge=0, le=8, description="Quantidade de banheiros no imóvel")
    vagas: int = Field(ge=0, le=8, description="Quantidade de vagas de garagem no imóvel")

    # Variáveis Booleanas (Opcionais)
    piscina: bool = Field(default=False, description="")
    espaco_gourmet: bool = Field(default=False, description="")
    academia: bool = Field(default=False, description="")
    spa_massagem: bool = Field(default=False, description="")
    espaco_lazer: bool = Field(default=False, description="")
    area_trabalho: bool = Field(default=False, description="")
    espaco_infantil: bool = Field(default=False, description="")
    area_esportiva: bool = Field(default=False, description="")
    portaria: bool = Field(default=False, description="")
    seguranca: bool = Field(default=False, description="")
    servicos_garagem: bool = Field(default=False, description="")
    acessibilidade: bool = Field(default=False, description="")
    pets: bool = Field(default=False, description="")
    varanda: bool = Field(default=False, description="")
    area_verde: bool = Field(default=False, description="")
    espaco_natural: bool = Field(default=False, description="")
    acabamento_premium: bool = Field(default=False, description="")
    moveis_embutidos: bool = Field(default=False, description="")
    layout_premium: bool = Field(default=False, description="")
    cozinha: bool = Field(default=False, description="")
    servicos: bool = Field(default=False, description="")
    conforto_interno: bool = Field(default=False, description="")
    mobiliado: bool = Field(default=False, description="")
    casa_inteligente: bool = Field(default=False, description="")
    servicos_conectividade: bool = Field(default=False, description="")
    infra_energetica: bool = Field(default=False, description="")
    infra_hidrica: bool = Field(default=False, description="")
    servicos_sustentaveis: bool = Field(default=False, description="")

    # Variáveis Geográficas
    latitude: float = Field(default=float("nan"), ge=MIN_LATITUDE, le=MAX_LATITUDE, description="Latitude do imóvel")
    longitude: float = Field(default=float("nan"), ge=MIN_LONGITUDE, le=MAX_LONGITUDE, description="Longitude do imóvel")


class PredictionResponse(BaseModel):
    """Schema de resposta com a estimativa de preço calculada pelo modelo."""

    estimated_price: float = Field(
        ...,
        description="Valor estimado de venda do imóvel pelo modelo de Machine Learning.",
        examples=[1250000.0],
    )
    currency: str = Field(
        default="BRL",
        description="Código da moeda do valor estimado (padrão: Real Brasileiro).",
        examples=["BRL"],
    )


class HealthResponse(BaseModel):
    """Schema de resposta para checagem de saúde da API e status do modelo."""

    status: str = Field(default="healthy", description="Status geral da aplicação.")
    model_loaded: bool = Field(..., description="Indica se o modelo de ML está carregado na memória.")
