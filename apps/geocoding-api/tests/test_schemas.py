"""Testes unitários para validação de schemas Pydantic v2 da geocoding-api."""

import pytest
from pydantic import ValidationError

from src.schemas import (
    BatchGeocodingRequest,
    BatchReverseGeocodingRequest,
    BatchReverseGeocodingResponse,
    CoordinateRequest,
    GeocodingData,
    GeocodingResponse,
    HealthResponse,
    ReverseGeocodingResponse,
    ReverseGeocodingResult,
)


def test_geocoding_data_and_response_validation():
    """Valida a criação e serialização dos dados de geocodificação direta."""
    data = GeocodingData(
        place_id="1010",
        address="Avenida 85, Setor Sul",
        latitude=-16.69,
        longitude=-49.26,
        formatted_address="Avenida 85, Setor Sul, Goiânia, GO",
    )
    resp = GeocodingResponse(source="cache", data=data)

    assert resp.source == "cache"
    assert resp.data.latitude == -16.69
    assert resp.data.place_id == "1010"


def test_health_response_validation():
    """Valida o schema de diagnóstico de saúde."""
    health = HealthResponse(
        status="online",
        message="Todos os serviços operacionais.",
        database=True,
        nominatim=True,
    )
    assert health.status == "online"
    assert health.database is True
    assert health.nominatim is True


def test_batch_geocoding_request_boundaries():
    """Valida os limites mínimo (1) e máximo (100) para requisições em lote."""
    # Válido com 1 endereço
    req_valid = BatchGeocodingRequest(addresses=["Avenida Anhanguera"])
    assert len(req_valid.addresses) == 1

    # Válido com 100 endereços
    req_100 = BatchGeocodingRequest(addresses=[f"Rua {i}" for i in range(100)])
    assert len(req_100.addresses) == 100

    # Inválido: lista vazia (min_length=1)
    with pytest.raises(ValidationError):
        BatchGeocodingRequest(addresses=[])

    # Inválido: mais de 100 endereços (max_length=100)
    with pytest.raises(ValidationError):
        BatchGeocodingRequest(addresses=[f"Rua {i}" for i in range(101)])


def test_coordinate_request_boundaries():
    """Valida os limites matemáticos de latitude (-90 a 90) e longitude (-180 a 180)."""
    valid_coord = CoordinateRequest(latitude=-16.68, longitude=-49.25)
    assert valid_coord.latitude == -16.68
    assert valid_coord.longitude == -49.25

    # Latitude fora dos limites
    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=-90.1, longitude=0.0)

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=90.1, longitude=0.0)

    # Longitude fora dos limites
    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=0.0, longitude=-180.1)

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=0.0, longitude=180.1)


def test_batch_reverse_geocoding_boundaries():
    """Valida os limites para lote de geocodificação reversa."""
    valid_batch = BatchReverseGeocodingRequest(
        coordinates=[CoordinateRequest(latitude=-16.68, longitude=-49.25)]
    )
    assert len(valid_batch.coordinates) == 1

    # Vazio
    with pytest.raises(ValidationError):
        BatchReverseGeocodingRequest(coordinates=[])

    # Mais de 100
    with pytest.raises(ValidationError):
        BatchReverseGeocodingRequest(
            coordinates=[
                CoordinateRequest(latitude=0.0, longitude=0.0) for _ in range(101)
            ]
        )


def test_reverse_geocoding_response_and_result():
    """Valida resposta unitária e em lote de geocodificação reversa."""
    coord = CoordinateRequest(latitude=-16.68, longitude=-49.25)
    rev_resp = ReverseGeocodingResponse(
        source="nominatim", data={"display_name": "Goiânia, GO"}
    )
    assert rev_resp.source == "nominatim"
    assert rev_resp.data["display_name"] == "Goiânia, GO"

    result = ReverseGeocodingResult(
        query=coord,
        source="cache",
        data={"road": "Avenida Anhanguera"},
    )
    assert result.query.latitude == -16.68
    assert result.source == "cache"

    batch_resp = BatchReverseGeocodingResponse(results=[result])
    assert len(batch_resp.results) == 1
    assert batch_resp.results[0].source == "cache"
