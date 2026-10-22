"""Testes unitários para validação de schemas Pydantic (schemas.py)."""

import math
from typing import Any

import pytest
from pydantic import ValidationError

from src.schemas import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    HealthResponse,
    InferenceRequest,
    PredictionResponse,
)


def test_inference_request_valid_minimal(valid_payload_minimal: dict[str, Any]):
    """Valida que o schema aceita apenas os campos obrigatórios e aplica defaults corretos."""
    req = InferenceRequest.model_validate(valid_payload_minimal)

    assert req.tipo_imovel == "casa"
    assert req.condominio == 0
    assert req.area_m2 == 150
    assert req.quartos == 4
    assert req.banheiros == 3
    assert req.vagas == 2

    # Verifica se as amenidades booleanas assumiram False por padrão
    assert req.piscina is False
    assert req.espaco_gourmet is False
    assert req.academia is False
    assert req.spa_massagem is False
    assert req.portaria is False
    assert req.seguranca is False
    assert req.mobiliado is False
    assert req.casa_inteligente is False

    # Coordenadas geográficas devem ser NaN por padrão
    assert math.isnan(req.latitude)
    assert math.isnan(req.longitude)


def test_inference_request_valid_all_features(
    valid_payload_all_features: dict[str, Any],
):
    """Valida instanciação completa com todas as features e coordenadas válidas."""
    req = InferenceRequest.model_validate(valid_payload_all_features)

    assert req.tipo_imovel == "cobertura"
    assert req.condominio == 1800
    assert req.area_m2 == 240
    assert req.quartos == 4
    assert req.banheiros == 5
    assert req.vagas == 4
    assert req.piscina is True
    assert req.spa_massagem is False
    assert req.latitude == -16.705
    assert req.longitude == -49.261


@pytest.mark.parametrize(
    "tipo",
    ["apartamento", "casa", "cobertura", "sobrado", "flat", "studio", "outro"],
)
def test_inference_request_valid_tipo_imovel(
    tipo: str, valid_payload_minimal: dict[str, Any]
):
    """Valida todos os tipos literais de imóvel permitidos."""
    payload = {**valid_payload_minimal, "tipo_imovel": tipo}
    req = InferenceRequest.model_validate(payload)
    assert req.tipo_imovel == tipo


@pytest.mark.parametrize(
    "tipo_invalido",
    ["mansao", "terreno", "fazenda", "chacara", "", "Apartamento"],
)
def test_inference_request_invalid_tipo_imovel(
    tipo_invalido: str, valid_payload_minimal: dict[str, Any]
):
    """Rejeita tipos de imóvel fora da lista permitida."""
    payload = {**valid_payload_minimal, "tipo_imovel": tipo_invalido}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize("condominio", [0, 1, 2500, 5000])
def test_inference_request_valid_condominio_range(
    condominio: int, valid_payload_minimal: dict[str, Any]
):
    """Valida valores no intervalo permitido de condomínio (0 a 5000)."""
    payload = {**valid_payload_minimal, "condominio": condominio}
    req = InferenceRequest.model_validate(payload)
    assert req.condominio == condominio


@pytest.mark.parametrize("condominio_invalido", [-1, -500, 5001, 10000])
def test_inference_request_invalid_condominio_range(
    condominio_invalido: int, valid_payload_minimal: dict[str, Any]
):
    """Rejeita valores fora dos limites para condomínio."""
    payload = {**valid_payload_minimal, "condominio": condominio_invalido}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize("area", [20, 21, 500, 1000])
def test_inference_request_valid_area_m2_range(
    area: int, valid_payload_minimal: dict[str, Any]
):
    """Valida valores no intervalo permitido de área útil (20 a 1000 m²)."""
    payload = {**valid_payload_minimal, "area_m2": area}
    req = InferenceRequest.model_validate(payload)
    assert req.area_m2 == area


@pytest.mark.parametrize("area_invalida", [19, 0, -5, 1001, 2500])
def test_inference_request_invalid_area_m2_range(
    area_invalida: int, valid_payload_minimal: dict[str, Any]
):
    """Rejeita valores de área útil fora do intervalo 20 a 1000 m²."""
    payload = {**valid_payload_minimal, "area_m2": area_invalida}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize("field_name", ["quartos", "banheiros", "vagas"])
@pytest.mark.parametrize("valid_val", [0, 1, 4, 8])
def test_inference_request_valid_rooms_ranges(
    field_name: str, valid_val: int, valid_payload_minimal: dict[str, Any]
):
    """Valida limites numéricos (0 a 8) para quartos, banheiros e vagas."""
    payload = {**valid_payload_minimal, field_name: valid_val}
    req = InferenceRequest.model_validate(payload)
    assert getattr(req, field_name) == valid_val


@pytest.mark.parametrize("field_name", ["quartos", "banheiros", "vagas"])
@pytest.mark.parametrize("invalid_val", [-1, 9, 100])
def test_inference_request_invalid_rooms_ranges(
    field_name: str, invalid_val: int, valid_payload_minimal: dict[str, Any]
):
    """Rejeita valores menores que 0 ou maiores que 8 para quartos, banheiros e vagas."""
    payload = {**valid_payload_minimal, field_name: invalid_val}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize("lat", [MIN_LATITUDE, -16.70, MAX_LATITUDE])
def test_inference_request_valid_latitude(
    lat: float, valid_payload_minimal: dict[str, Any]
):
    """Valida latitude dentro do bounding box de Goiânia."""
    payload = {**valid_payload_minimal, "latitude": lat}
    req = InferenceRequest.model_validate(payload)
    assert req.latitude == lat


@pytest.mark.parametrize(
    "lat_invalida",
    [MIN_LATITUDE - 0.001, MAX_LATITUDE + 0.001, -23.55, 0.0, 10.0],
)
def test_inference_request_invalid_latitude(
    lat_invalida: float, valid_payload_minimal: dict[str, Any]
):
    """Rejeita latitude fora do bounding box de Goiânia."""
    payload = {**valid_payload_minimal, "latitude": lat_invalida}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize("lon", [MIN_LONGITUDE, -49.30, MAX_LONGITUDE])
def test_inference_request_valid_longitude(
    lon: float, valid_payload_minimal: dict[str, Any]
):
    """Valida longitude dentro do bounding box de Goiânia."""
    payload = {**valid_payload_minimal, "longitude": lon}
    req = InferenceRequest.model_validate(payload)
    assert req.longitude == lon


@pytest.mark.parametrize(
    "lon_invalida",
    [MIN_LONGITUDE - 0.001, MAX_LONGITUDE + 0.001, -46.63, 0.0, 10.0],
)
def test_inference_request_invalid_longitude(
    lon_invalida: float, valid_payload_minimal: dict[str, Any]
):
    """Rejeita longitude fora do bounding box de Goiânia."""
    payload = {**valid_payload_minimal, "longitude": lon_invalida}
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


@pytest.mark.parametrize(
    "required_field",
    ["tipo_imovel", "condominio", "area_m2", "quartos", "banheiros", "vagas"],
)
def test_inference_request_missing_required_fields(
    required_field: str, valid_payload_minimal: dict[str, Any]
):
    """Garante que a ausência de qualquer campo obrigatório dispara ValidationError."""
    payload = valid_payload_minimal.copy()
    del payload[required_field]
    with pytest.raises(ValidationError):
        InferenceRequest.model_validate(payload)


def test_prediction_response_schema():
    """Valida valores padrão e serialização de PredictionResponse."""
    resp = PredictionResponse(estimated_price=850000.0)
    assert resp.estimated_price == 850000.0
    assert resp.currency == "BRL"

    dumped = resp.model_dump()
    assert dumped == {"estimated_price": 850000.0, "currency": "BRL"}

    custom_resp = PredictionResponse(estimated_price=120000.0, currency="USD")
    assert custom_resp.currency == "USD"


def test_health_response_schema():
    """Valida criação e valores de HealthResponse."""
    resp_healthy = HealthResponse(model_loaded=True)
    assert resp_healthy.status == "healthy"
    assert resp_healthy.model_loaded is True

    resp_unloaded = HealthResponse(model_loaded=False)
    assert resp_unloaded.status == "healthy"
    assert resp_unloaded.model_loaded is False

    resp_custom = HealthResponse(status="degraded", model_loaded=False)
    assert resp_custom.status == "degraded"
    assert resp_custom.model_loaded is False
