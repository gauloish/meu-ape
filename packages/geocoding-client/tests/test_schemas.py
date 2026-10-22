"""Testes unitários para schemas Pydantic do geocoding-client (schemas.py)."""

import pytest
from geocoding_client.schemas import (
    BatchGeocodingRequest,
    BatchGeocodingResponse,
    BatchReverseGeocodingRequest,
    BatchReverseGeocodingResponse,
    CoordinateRequest,
    GeocodingData,
    GeocodingResponse,
    HealthResponse,
    ReverseGeocodingResponse,
    ReverseGeocodingResult,
)
from pydantic import ValidationError


def test_geocoding_data_and_response():
    """Valida schemas GeocodingData e GeocodingResponse."""
    data = GeocodingData(
        place_id="123",
        address="Avenida Anhanguera",
        latitude=-16.68,
        longitude=-49.25,
        formatted_address="Avenida Anhanguera, Goiânia, GO",
    )
    assert data.latitude == -16.68
    assert data.place_id == "123"

    resp = GeocodingResponse(source="cache", data=data)
    assert resp.source == "cache"
    assert resp.data is not None
    assert resp.data.address == "Avenida Anhanguera"


def test_coordinate_request_boundaries():
    """Valida limites de latitude [-90, 90] e longitude [-180, 180]."""
    valid_coord = CoordinateRequest(latitude=-16.68, longitude=-49.25)
    assert valid_coord.latitude == -16.68

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=-90.1, longitude=-49.25)

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=90.1, longitude=-49.25)

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=-16.68, longitude=-180.1)

    with pytest.raises(ValidationError):
        CoordinateRequest(latitude=-16.68, longitude=180.1)


def test_batch_requests_and_responses():
    """Valida schemas de requisição e resposta em lote."""
    batch_req = BatchGeocodingRequest(addresses=["Rua 1", "Rua 2"])
    assert len(batch_req.addresses) == 2

    batch_resp = BatchGeocodingResponse(
        results=[
            GeocodingResponse(source="cache", data=None),
        ]
    )
    assert len(batch_resp.results) == 1

    rev_batch_req = BatchReverseGeocodingRequest(
        coordinates=[CoordinateRequest(latitude=-16.68, longitude=-49.25)]
    )
    assert len(rev_batch_req.coordinates) == 1

    rev_batch_resp = BatchReverseGeocodingResponse(
        results=[
            ReverseGeocodingResult(
                query=CoordinateRequest(latitude=-16.68, longitude=-49.25),
                source="nominatim",
                data={"road": "Avenida Goiás"},
            )
        ]
    )
    assert len(rev_batch_resp.results) == 1


def test_health_response():
    """Valida schema HealthResponse."""
    health = HealthResponse(
        status="online",
        message="Serviço ativo",
        database=True,
        nominatim=True,
    )
    assert health.status == "online"
    assert health.database is True
    assert health.nominatim is True


def test_reverse_geocoding_response():
    """Valida schema ReverseGeocodingResponse."""
    resp = ReverseGeocodingResponse(source="cache", data={"city": "Goiânia"})
    assert resp.source == "cache"
    assert resp.data == {"city": "Goiânia"}
