"""Testes unitários para os modelos ORM SQLAlchemy de cache da geocoding-api."""

import json

from src.database.models import GeocodingCache, ReverseGeocodingCache


def test_geocoding_cache_model():
    """Valida a instanciação e representação textual de GeocodingCache."""
    entry = GeocodingCache(
        address="avenida anhanguera",
        latitude=-16.6868,
        longitude=-49.2648,
        formatted_address="Avenida Anhanguera, Goiânia, GO",
        place_id="98765",
    )

    assert entry.address == "avenida anhanguera"
    assert entry.latitude == -16.6868
    assert entry.longitude == -49.2648
    assert entry.place_id == "98765"
    assert "GeocodingCache" in repr(entry)
    assert "-16.6868" in repr(entry)


def test_reverse_geocoding_cache_model():
    """Valida a instanciação, geração de chave e desserialização JSON de ReverseGeocodingCache."""
    key = ReverseGeocodingCache.make_key(-16.6868123, -49.2648123, precision=5)
    assert key == "-16.68681,-49.26481"

    data_payload = {"road": "Avenida Anhanguera", "city": "Goiânia"}
    entry = ReverseGeocodingCache(
        coord_key=key,
        latitude=-16.68681,
        longitude=-49.26481,
        raw_data_json=json.dumps(data_payload),
    )

    assert entry.coord_key == key
    assert entry.get_data() == data_payload
    assert "ReverseGeocodingCache" in repr(entry)
