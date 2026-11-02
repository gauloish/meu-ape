"""Suíte de testes unitários para o parser de anúncios JSON-LD do Zap Imóveis."""

from datetime import datetime

from src.scraping.zap_parser import (
    _extract_condo_fee,
    _extract_neighbourhood,
    _extract_parking_spots,
    _extract_property_type,
    _join_photo_urls,
    parse_item,
)

RAW_ITEM = {
    "@id": "2771234567",
    "name": "Apartamento com 3 Quartos e 2 vagas à venda, 90m² em Setor Bueno, Goiânia",
    "additionalType": "https://schema.org/Apartment",
    "url": "https://www.zapimoveis.com.br/imovel/2771234567/",
    "offers": {
        "price": 650000,
        "priceCurrency": "BRL",
        "additionalProperty": {"name": "Condominium Fee", "value": 550},
    },
    "address": {
        "streetAddress": "Rua T-55",
        "addressLocality": "Goiânia",
        "addressRegion": "GO",
        "addressCountry": "BR",
    },
    "floorSize": {"value": 90},
    "numberOfBedrooms": 3,
    "numberOfBathroomsTotal": 2,
    "petsAllowed": "true",
    "amenityFeature": [
        {"value": "Piscina"},
        {"value": "Academia"},
        {"name": "sem valor"},
    ],
    "image": ["https://img/1.jpg", "https://img/2.jpg"],
    "description": "Ótimo apartamento.",
    "datePublished": "2026-10-30",
    "dateModified": "2026-10-31",
}


def test_parse_item_maps_all_fields():
    """Valida o mapeamento completo de um item JSON-LD para o registro tabular."""
    record = parse_item(RAW_ITEM)

    assert record["id"] == "2771234567"
    assert record["tipo_imovel"] == "Apartment"
    assert record["preco"] == 650000
    assert record["moeda"] == "BRL"
    assert record["condominio"] == 550
    assert record["area_m2"] == 90
    assert record["quartos"] == 3
    assert record["banheiros"] == 2
    assert record["vagas"] == 2
    assert record["bairro"] == "Setor Bueno"
    assert record["rua"] == "Rua T-55"
    assert record["cidade"] == "Goiânia"
    assert record["comodidades"] == "Piscina, Academia"
    assert record["fotos_urls"] == "https://img/1.jpg, https://img/2.jpg"
    assert record["data_publicacao"] == "2026-10-30"
    datetime.fromisoformat(record["scraped_at"])


def test_parse_item_handles_missing_nested_objects():
    """Valida que campos aninhados ausentes ou malformados resultam em None sem exceções."""
    record = parse_item({"@id": "1", "offers": "inválido", "address": None})

    assert record["id"] == "1"
    assert record["preco"] is None
    assert record["moeda"] == "BRL"
    assert record["rua"] is None
    assert record["area_m2"] is None
    assert record["tipo_imovel"] is None
    assert record["comodidades"] == ""
    assert record["fotos_urls"] == ""


def test_parse_item_falls_back_to_number_of_rooms():
    """Valida o uso de numberOfRooms quando numberOfBedrooms está ausente."""
    record = parse_item({"numberOfRooms": 4})
    assert record["quartos"] == 4


def test_extract_parking_spots():
    """Valida a extração da quantidade de vagas a partir do título."""
    assert _extract_parking_spots("Casa com 1 vaga") == 1
    assert _extract_parking_spots("Casa com 3 Vagas") == 3
    assert _extract_parking_spots("Casa sem garagem") is None


def test_extract_neighbourhood():
    """Valida a extração do bairro a partir do título."""
    assert (
        _extract_neighbourhood("Casa à venda em Jardim Goiás, Goiânia")
        == "Jardim Goiás"
    )
    assert _extract_neighbourhood("Casa à venda") is None


def test_extract_property_type():
    """Valida a derivação do tipo de imóvel por additionalType ou pela primeira palavra do título."""
    assert (
        _extract_property_type({"additionalType": "https://schema.org/House"}, "x")
        == "House"
    )
    assert _extract_property_type({}, "Sobrado com 3 quartos") == "Sobrado"
    assert _extract_property_type({}, "") is None


def test_join_photo_urls():
    """Valida a formatação das URLs de fotos."""
    assert _join_photo_urls(["a", "b"]) == "a, b"
    assert _join_photo_urls("a") == "a"
    assert _join_photo_urls(None) == ""


def test_extract_condo_fee():
    """Valida a extração da taxa de condomínio apenas quando a propriedade correta está presente."""
    assert (
        _extract_condo_fee(
            {"additionalProperty": {"name": "Condominium Fee", "value": 300}}
        )
        == 300
    )
    assert (
        _extract_condo_fee({"additionalProperty": {"name": "IPTU", "value": 100}})
        is None
    )
    assert _extract_condo_fee({}) is None
