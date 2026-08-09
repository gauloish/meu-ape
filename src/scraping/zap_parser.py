"""ZAP Imóveis property listing parser module.

Provides a unified parsing interface to convert raw JSON-LD structured data items
retrieved from Zap Imóveis web pages into normalised dictionary records.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _extract_parking_spots(title: str) -> Optional[int]:
    """Extract the count of parking spots from a listing title.

    Args:
        title: Raw title string from the property listing.

    Returns:
        Number of parking spots if matched, otherwise None.
    """
    match = re.search(r"(\d+)\s+vagas?", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_neighbourhood(title: str) -> Optional[str]:
    """Extract the neighbourhood name from a listing title.

    Args:
        title: Raw title string from the property listing.

    Returns:
        Neighbourhood string if matched, otherwise None.
    """
    match = re.search(r"em\s+(.+?),\s*(?:Goiânia|GO|Brasil)", title, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_property_type(item: Dict[str, Any], title: str) -> Optional[str]:
    """Derive property type from additionalType or listing title.

    Args:
        item: Raw item dictionary from JSON-LD schema.
        title: Raw title string from the property listing.

    Returns:
        Extracted property type string or None.
    """
    add_type = item.get("additionalType", "")
    if "/" in str(add_type):
        return add_type.split("/")[-1]
    return title.split()[0] if title else None


def _join_photo_urls(images: Any) -> str:
    """Format image URL attributes into a comma-separated string."""
    if isinstance(images, list):
        return ", ".join(images)
    return str(images) if images else ""


def _extract_condo_fee(offers: Dict[str, Any]) -> Optional[float]:
    """Extract condominium fee from additional properties dict."""
    add_prop = offers.get("additionalProperty", {})
    if isinstance(add_prop, dict) and add_prop.get("name") == "Condominium Fee":
        return add_prop.get("value")
    return None


def parse_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a raw JSON-LD listing object into a tabular dictionary.

    Args:
        item: Dictionary corresponding to an ItemList entry from Zap Imóveis
            structured HTML data.

    Returns:
        A dictionary containing normalised property fields ready for DataFrame
        export or CSV persistence.
    """
    offers: Dict[str, Any] = item.get("offers", {}) if isinstance(item.get("offers"), dict) else {}
    address: Dict[str, Any] = item.get("address", {}) if isinstance(item.get("address"), dict) else {}
    floor_size: Dict[str, Any] = item.get("floorSize", {}) if isinstance(item.get("floorSize"), dict) else {}

    title: str = item.get("name", "") or ""

    amenities = [
        af["value"]
        for af in item.get("amenityFeature", [])
        if isinstance(af, dict) and af.get("value")
    ]

    return {
        "id": item.get("@id"),
        "titulo": title,
        "tipo_imovel": _extract_property_type(item, title),
        "url": item.get("url"),
        "preco": offers.get("price"),
        "moeda": offers.get("priceCurrency", "BRL"),
        "condominio": _extract_condo_fee(offers),
        "area_m2": floor_size.get("value"),
        "quartos": item.get("numberOfBedrooms") or item.get("numberOfRooms"),
        "banheiros": item.get("numberOfBathroomsTotal"),
        "vagas": _extract_parking_spots(title),
        "bairro": _extract_neighbourhood(title),
        "rua": address.get("streetAddress"),
        "cidade": address.get("addressLocality"),
        "estado": address.get("addressRegion"),
        "pais": address.get("addressCountry"),
        "aceita_pets": item.get("petsAllowed"),
        "comodidades": ", ".join(amenities),
        "fotos_urls": _join_photo_urls(item.get("image", [])),
        "descricao_completa": item.get("description"),
        "data_publicacao": item.get("datePublished"),
        "data_modificacao": item.get("dateModified"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
